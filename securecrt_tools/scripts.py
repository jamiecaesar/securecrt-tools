"""
This module contains classes for representing the execution of the script and wraps the underlying API calls used to
interact with the that application itself.  This is primarily SecureCRT, but will also include a sub-class to
simulate connecting to devices when running the scripts directly.  Running the script directly from your local python
interpreter is used for troubleshooting the script using an IDE such as PyCharm, Spyder, Eclipse, etc.

The Script class is responsible for tasks such as interacting with the user (displaying messages, prompting for input,
etc), interacting with the file system, and modifying the application (creating new saved sessions)

"""

import os
import sys
import logging
import datetime
import csv
from abc import ABCMeta, abstractmethod
import sessions
from settings import SettingsImporter
from message_box_const import *


# ################################################    EXCEPTIONS     ###################################################


class ScriptError(Exception):
    """
    An exception type that is raised when there is a problem with the main scripts, such as missing settings files.
    """
    pass


# ################################################    APP  CLASSES    ##################################################

class Script:
    """
    This is a base class for the application object.  This class simply exists to enforce the required methods any
    Application sub-classes must implement.  Any methods that would operate the same, regardless of which Application
    they are for would also be defined here and inherited by the subclasses.
    """
    __metaclass__ = ABCMeta

    def __init__(self, script_path):
        # Initialize application attributes
        self.script_dir, self.script_name = os.path.split(script_path)
        self.logger = logging
        self.main_session = None

        # Load Settings
        settings_file = os.path.join(self.script_dir, "settings", "settings.ini")
        try:
            self.settings = SettingsImporter(settings_file)
        except IOError:
            error_msg = "A settings file at {} does not exist.  Do you want to create it?".format(settings_file)
            result = self.message_box(error_msg, "Missing Settings File", ICON_QUESTION | BUTTON_YESNO)
            if result == IDYES:
                self.settings = SettingsImporter(settings_file, create=True)
            else:
                raise ScriptError("Settings file not found")

        # Get the date and time to use in output file names
        now = datetime.datetime.now()
        date_format = self.settings.get("Global", "date_format")
        self.datetime = now.strftime(date_format)

        # Extract and store "save path" for future reference by scripts.
        output_dir = self.settings.get("Global", "output_dir")
        exp_output_dir = os.path.expandvars(os.path.expanduser(output_dir))
        if os.path.isabs(exp_output_dir):
            self.output_dir = os.path.realpath(exp_output_dir)
        else:
            full_path = os.path.join(self.script_dir, exp_output_dir)
            self.output_dir = os.path.realpath(full_path)
        self.validate_dir(self.output_dir)

        # Check if Debug Mode is enabled.
        if self.settings.getboolean("Global", "debug_mode"):
            self.debug_dir = os.path.join(self.output_dir, "debugs")
            self.validate_dir(self.debug_dir)
            log_file = os.path.join(self.debug_dir, self.script_name.replace(".py", "-debug.txt"))
            self.logger = logging.getLogger("securecrt")
            self.logger.propagate = False
            self.logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S')
            fh = logging.FileHandler(log_file, mode='w')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            self.logger.debug("<SCRIPT_INIT> Starting Logging. Running Python version: {0}".format(sys.version))

    def get_main_session(self):
        """
        Returns a CRTSession object that interacts with the SecureCRT tab that the script was lauched within.  This is
        the primary tab that will be used to interact with remote devices.  While new tabs can be created to connect to
        other devices, SecureCRT does not support multi-threading so multiple devices cannot be interacted with
        simultaneously via a script.

        :return: A session object that represents the tab where the script was launched
        :rtype: sessions.Session
        """
        return self.main_session

    def validate_dir(self, path):
        """
        Verifies that the path to the supplied directory exists.  If not, prompt the user to create it.

        :param path: A directory path (not including filename) to be validated
        :type path: str
        """

        self.logger.debug("<VALIDATE_PATH> Starting validation of path: {0}".format(path))

        # Verify that base_path is valid absolute path, or else error and exit.
        if not os.path.isabs(path):
            self.logger.debug("<VALIDATE_PATH> Supplied path is not an absolute path. Raising exception".format(path))
            error_str = 'Directory {} is invalid.'.format(path)
            raise IOError(error_str)

        # Check if directory exists.  If not, prompt to create it.
        if not os.path.exists(os.path.normpath(path)):
            self.logger.debug("<VALIDATE_PATH> Supplied directory path does not exist. Prompting User.")
            message_str = "The path: '{}' does not exist.  Do you want to create it?.".format(path)
            result = self.message_box(message_str, "Create Directory?", ICON_QUESTION | BUTTON_YESNO | DEFBUTTON2)

            if result == IDYES:
                self.logger.debug("<VALIDATE_PATH> User chose to create directory.".format(path))
                os.makedirs(path)
            else:
                self.logger.debug("<VALIDATE_PATH> User chose NOT to create directory.  Raising exception")
                error_str = 'Required directory {} does not exist.'.format(path)
                raise IOError(error_str)
        self.logger.debug("<VALIDATE_PATH> Path is Valid.")

    def get_template(self, name):
        """
        Retrieve the full path to a TextFSM template file.

        :param name: Filename of the template
        :type name: str

        :return: Full path to the template location
        :rtype: str
        """
        path = os.path.abspath(os.path.join(self.script_dir, "textfsm-templates", name))
        if os.path.isfile(path):
            return path
        else:
            raise IOError("The template name {} does not exist.")

    def import_device_list(self):
        """
        This function will prompt for a device list CSV file to import, returns a list containing all of the
        devices that were in the CSV file and their associated credentials.  The CSV file must be of the format, and
        include a header row of ['Hostname', 'Protocol', 'Username', 'Password', 'Enable', 'Via-Jumpbox'].  An example
        device list CSV file is at 'template/sample_device_list.csv'

        Some additional information about missing items from a line in the CSV:
        - If the hostname field is missing, the line will be skipped.
        - If the protocol field is empty, the script will try SSH2, then SSH1, then Telnet.
        - If the username is missing, this method will prompt the user for a default usernaem to use
        - If the password is missing, will prompt the user for a password for each username missing a password
        - If the enable password is missing, the method will ask the user if they want to set a default enable to use
        - If the IP is included then the device will be reached through the jumpbox, otherwise connect directly.

        :return: A list where each entry is a dictionary representing a device and the associated login information.
        :rtype: list of dict
        """
        # Get the filename of the device list CSV file.
        self.logger.debug("<IMPORT_DEVICES> Prompting for input CSV file.")
        device_list_filename = ""
        device_list_filename = self.file_open_dialog("Please select a device list CSV file.", "Open",
                                                     device_list_filename, "CSV Files (*.csv)|*.csv||")
        if device_list_filename == "":
            self.logger.debug("<IMPORT_DEVICES> No filename received from dialog window.  Exiting.")
            return

        self.logger.debug("<IMPORT_DEVICES> Starting processing of device CSV file.")
        # Track how many lines of the CSV are skipped.
        skipped_lines = 0

        # The username that will be used when one isn't given in the CSV.  This will be prompted for when an empty
        # username field is found.
        default_username = None
        credentials = {}
        no_password = set()
        no_enable = False
        temp_device_list = []

        # Extract the list of devices into a data structure we can use (and fill in any gaps needed).
        with open(device_list_filename, 'r') as device_file:
            device_csv = csv.reader(device_file)

            # Get header line and validate it is correct.
            header = next(device_csv, None)
            if header != ['Hostname', 'Protocol', 'Username', 'Password', 'Enable']:
                raise ScriptError("CSV file does not have a valid header row.")

            # Loop through all lines of the CSV, and decide if any information is missing.
            for line in device_csv:
                hostname = line[0].strip()
                protocol = line[1].strip()
                username = line[2].strip()
                password = line[3].strip()
                enable = line[4].strip()

                if not hostname:
                    self.logger.debug("<IMPORT_DEVICES> Skipping CSV line {} because no hostname exists.".format(line))
                    skipped_lines += 1
                    continue

                if protocol.lower() not in ['', 'ssh', 'ssh1', 'ssh2', 'telnet']:
                    self.logger.debug("<IMPORT_DEVICES> Skipping CSV line {} because no valid protocol.".format(line))
                    skipped_lines += 1
                    continue

                if not username:
                    if default_username:
                        username = default_username
                        self.logger.debug("<IMPORT_DEVICES> Using default username '{}', for host {}."
                                          .format(default_username, hostname))
                    else:
                        self.logger.debug("<IMPORT_DEVICES> Didn't find username for host '{}'.  Prompting for DEFAULT."
                                          .format(hostname))
                        default_username = self.prompt_window("Enter the DEFAULT USERNAME to use.")
                        if default_username == '':
                            self.logger.debug("<IMPORT_DEVICES> Default username not provided.  Stopping".format(line))
                            error = "Found hosts without usernames and no default username provided."
                            raise ScriptError(error)
                        else:
                            self.logger.debug("<IMPORT_DEVICES> Using default username '{}', for host {}."
                                              .format(default_username, hostname))
                            username = default_username

                if not password:
                    no_password.add(username)

                if not enable:
                    no_enable = True

                temp_device_list.append([hostname, protocol, username, password, enable])

        # Prompt for missing information
        for username in no_password:
            self.logger.debug("<IMPORT_DEVICES> Prompting for password for username '{}'".format(username))
            password = self.prompt_window("Enter the password for {}".format(username), hide_input=True)
            credentials[username] = password

        default_enable = None
        if no_enable:
            self.logger.debug("<IMPORT_DEVICES> Devices without enable passwords found.  Prompting fopr password.")
            enable_msg = "Devices were found without enable passwords listed.  Do you want to enter an enable password?"
            result = self.message_box(enable_msg, "No Enable PW", BUTTON_YESNO | ICON_QUESTION)
            if result == IDYES:
                default_enable = self.prompt_window("Enter default ENABLE password", "Enter Enable", hide_input=True)

        device_list = []
        # Make second run through device_list filling in the missing values, and create dictionary
        for line in temp_device_list:
            # Create a dict with all the information for this host
            dev_info = {'hostname': line[0], 'protocol': line[1]}

            # Fill in user information
            username = line[2]
            if username:
                dev_info['username'] = username
            else:
                dev_info['username'] = default_username

            # Fill in password information
            password = line[3]
            if not password:
                try:
                    dev_info['password'] = credentials[username]
                except KeyError:
                    self.logger.debug("<IMPORT_DEVICES> Skipping {}.  No password for user.".format(line[0]))
                    skipped_lines += 1
                    continue

            # Fill in enable information
            enable = line[4]
            if not enable and default_enable:
                enable = default_enable
            dev_info['enable'] = enable

            # Add this device to our dictionary:
            device_list.append(dev_info)

        # Give stats on how many devices were found and prompt user before going forward with connections.
        validate_message = "{} devices found in CSV.\n" \
                           "{} lines in CSV skipped.\n" \
                           "\n" \
                           "Do you want to proceed?".format(len(temp_device_list), skipped_lines)
        message_box_design = ICON_QUESTION | BUTTON_CANCEL | DEFBUTTON2
        self.logger.debug("<IMPORT_DEVICES> Prompting the user to continue with updates.")
        result = self.message_box(validate_message, "Ready to Start?", message_box_design)

        # IF user cancels, end program.
        if result == IDCANCEL:
            self.logger.debug("<IMPORT_DEVICES> User chose to cancel the script.")
            return

        return device_list

    @abstractmethod
    def message_box(self, message, title="", options=0):
        """
        Prints a message for the user.  In SecureCRT, the message is displayed in a pop-up message box.  When used in a
        DirectSession, the message is printed to the console and the user is prompted to type the button that would be
        selected.

        This window can be customized by setting the "options" value, using the constants listed at the top of the
        sessions.py file.  One constant from each of the 3 categories can be OR'd (|) together to make a single option
        value that will format the message box.

        :param message: The message to send to the user
        :type message: str
        :param title: Title for the message box
        :type title: str
        :param options: Sets the display format of the messagebox. (See Message Box constants in sessions.py)
        :type options: int

        :return: The return code that identifies which button the user pressed. (See Message Box constants)
        :rtype: int
        """
        # TODO Re-write this function to avoid needing to import constants to know how to modify the message box.
        pass

    @abstractmethod
    def prompt_window(self, message, title="", hide_input=False):
        """
        Prompts the user for an input value.  In SecureCRT this will open a pop-up window where the user can input the
        requested information.  In a direct session, the user will be prompted at the console for input.

        The "hide_input" input will mask the input, so that passwords or other senstive information can be requested.

        :param message: The message to send to the user
        :type message: str
        :param title: Title for the prompt window
        :type title: str
        :param hide_input: Specifies whether to hide the user input or not.  Default is False.
        :type hide_input: bool

        :return: The value entered by the user
        :rtype: str
        """
        pass

    @abstractmethod
    def file_open_dialog(self, title, button_label="Open", default_filename="", file_filter=""):
        """
        Prompts the user to select a file that will be processed by the script.  In SecureCRT this will give a pop-up
        file selection dialog window.  For a direct session, the user will be prompted for the full path to a file.
        See the SecureCRT built-in Help at Scripting > Script Objects Reference > Dialog Object for more details.

        :param title: <String> Title for the File Open dialog window (Only displays in Windows)
        :param button_label: <String> Label for the "Open" button
        :param default_filename: <String> If provided a default filename, the window will open in the parent directory
            of the file, otherwise the current working directory will be the starting directory.
        :param file_filter: <String> Specifies a filter for what type of files can be selected.  The format is:
            <Name of Filter> (*.<extension>)|*.<extension>||
            For example, a filter for CSV files would be "CSV Files (*.csv)|*.csv||" or multiple filters can be used:
            "Text Files (*.txt)|*.txt|Log File (*.log)|*.log||"

        :return: The absolute path to the file that was selected
        :rtype: str
        """
        pass

    @abstractmethod
    def ssh_in_new_tab(self, host, username, password, prompt_endings=("#", ">")):
        """
        Connects to a device via the SSH protocol in a new tab.  A new CRTSession object that controls the new tab is
        returned by this method.

        By default, SSH2 will be tried first, but if it fails it will attempt to fall back to SSH1.

        :param host: The IP address of DNS name for the device to connect
        :type host: str
        :param username: The username to login to the device with
        :type username: str
        :param password: The password that goes with the provided username.  If a password is not specified, the
                         user will be prompted for one.
        :type password: str
        :param prompt_endings: A list of strings that are possible prompt endings to watch for.  The default is for
                               Cisco devices (">" and "#"), but may need to be changed if connecting to another
                               type of device (for example "$" for some linux hosts).
        :type prompt_endings: list
        """
        pass

    @abstractmethod
    def create_new_saved_session(self, session_name, ip, protocol="SSH2", folder="_imports"):
        """
        Creates a session object that can be opened from the Connect menu in SecureCRT.

        :param session_name: The name of the session
        :type session_name: str
        :param ip: The IP address or hostname of the device represented by this session
        :type ip: str
        :param protocol: The protocol to use for this connection (TELNET, SSH1, SSH2, etc)
        :type protocol: str
        :param folder: The folder (starting from the configured Sessions folder) where this session should be saved.
        :type folder: str
        """
        pass


class CRTScript(Script):
    """
    This sub-class of the App class is used to wrap the portion of the SecureCRT API that interacts with the main
    application.
    """

    def __init__(self, crt):
        self.crt = crt
        super(CRTScript, self).__init__(crt.ScriptFullName)
        self.logger.debug("<SCRIPT_INIT> Starting creation of CRTScript object")

        # Set up SecureCRT tab for interaction with the scripts
        self.main_session = sessions.CRTSession(self, self.crt.GetScriptTab())

    def message_box(self, message, title="", options=0):
        """
        Prints a message for the user.  In SecureCRT, the message is displayed in a pop-up message box.  When used in a
        DirectSession, the message is printed to the console and the user is prompted to type the button that would be
        selected.

        This window can be customized by setting the "options" value, using the constants listed at the top of the
        sessions.py file.  One constant from each of the 3 categories can be OR'd (|) together to make a single option
        value that will format the message box.

        :param message: The message to send to the user
        :type message: str
        :param title: Title for the message box
        :type title: str
        :param options: Sets the display format of the messagebox. (See Message Box constants in sessions.py)
        :type options: int
        :return: The return code that identifies which button the user pressed. (See Message Box constants)
        :rtype: int
        """
        self.logger.debug("<MESSAGE_BOX> Creating MessageBox with: \nTitle: {}\nMessage: {}\nOptions: {}"
                          .format(title, message, options))
        return self.crt.Dialog.MessageBox(message, title, options)

    def prompt_window(self, message, title="", hide_input=False):
        """
        Prompts the user for an input value.  In SecureCRT this will open a pop-up window where the user can input the
        requested information.  In a direct session, the user will be prompted at the console for input.

        The "hide_input" input will mask the input, so that passwords or other senstive information can be requested.

        :param message: The message to send to the user
        :type message: str
        :param title: Title for the prompt window
        :type title: str
        :param hide_input: Specifies whether to hide the user input or not.  Default is False.
        :type hide_input: bool
        :return: The value entered by the user
        :rtype: str
        """
        self.logger.debug("<PROMPT> Creating Prompt with message: '{}'".format(message))
        result = self.crt.Dialog.Prompt(message, title, "", hide_input)
        self.logger.debug("<PROMPT> Captures prompt results: '{}'".format(result))
        return result

    def file_open_dialog(self, title, button_label="Open", default_filename="", file_filter=""):
        """
        Prompts the user to select a file that will be processed by the script.  In SecureCRT this will give a pop-up
        file selection dialog window.  For a direct session, the user will be prompted for the full path to a file.
        See the SecureCRT built-in Help at Scripting > Script Objects Reference > Dialog Object for more details.

        :param title: <String> Title for the File Open dialog window (Only displays in Windows)
        :param button_label: <String> Label for the "Open" button
        :param default_filename: <String> If provided a default filename, the window will open in the parent directory
            of the file, otherwise the current working directory will be the starting directory.
        :param file_filter: <String> Specifies a filter for what type of files can be selected.  The format is:
            <Name of Filter> (*.<extension>)|*.<extension>||
            For example, a filter for CSV files would be "CSV Files (*.csv)|*.csv||" or multiple filters can be used:
            "Text Files (*.txt)|*.txt|Log File (*.log)|*.log||"

        :return: The absolute path to the file that was selected
        :rtype: str
        """
        self.logger.debug("<FILE_OPEN> Creating File Open Dialog with title: '{}'".format(title))
        result_filename = self.crt.Dialog.FileOpenDialog(title, button_label, default_filename, file_filter)
        return result_filename

    def ssh_in_new_tab(self, host, username, password, prompt_endings=("#", ">")):
        """
        Connects to a device via the SSH protocol in a new tab.  A new CRTSession object that controls the new tab is
        returned by this method.

        By default, SSH2 will be tried first, but if it fails it will attempt to fall back to SSH1.

        :param host: The IP address of DNS name for the device to connect
        :type host: str
        :param username: The username to login to the device with
        :type username: str
        :param password: The password that goes with the provided username.  If a password is not specified, the
                         user will be prompted for one.
        :type password: str
        :param prompt_endings: A list of strings that are possible prompt endings to watch for.  The default is for
                               Cisco devices (">" and "#"), but may need to be changed if connecting to another
                               type of device (for example "$" for some linux hosts).
        :type prompt_endings: list
        """
        response_timeout = 10
        self.logger.debug("<NEW_TAB> Attempting new tab connection to: {}@{}".format(username, host))

        expanded_endings = []
        for ending in prompt_endings:
            expanded_endings.append("{}".format(ending))
            expanded_endings.append("{} ".format(ending))

        ssh2_string = "/SSH2 /ACCEPTHOSTKEYS /L {} /PASSWORD {} {}".format(username, password, host)
        self.logger.debug("<NEW_TAB> Attempting connection in a new tab.")
        new_tab = self.crt.Session.ConnectInTab(ssh2_string, failSilently=True)

        # Check if we successfully connected.  If not, try SSH1
        if not new_tab.Session.Connected:
            ssh1_string = "/SSH1 /ACCEPTHOSTKEYS /L {} /PASSWORD {} {}".format(username, password, host)
            self.logger.debug("<NEW_TAB> Attempting connection via SSH1 in existing new tab")
            new_tab.Session.Connect(ssh1_string)

            if not new_tab.Session.Connected:
                self.logger.debug("<NEW_TAB> SSH1 Failed.  Closing tab and raising exception.")
                new_tab.Close()
                raise sessions.ConnectError("Unabled to connect to {} in a new tab with SSH2 or SSH1.")

        # Set Tab parameters to allow correct sending/receiving of data via SecureCRT
        self.logger.debug("<NEW_TAB> Set Synchronous and IgnoreEscape")
        new_tab.Screen.Synchronous = True
        new_tab.Screen.IgnoreEscape = True

        self.logger.debug("<NEW_TAB> Started looking for following prompt endings: {}".format(expanded_endings))
        at_prompt = False
        while not at_prompt:
            found = new_tab.Screen.WaitForStrings(expanded_endings, response_timeout)
            if not found:
                raise sessions.InteractionError("Timeout reached looking for prompt endings: {}"
                                                .format(expanded_endings))
            else:
                test_string = "!@&^"
                new_tab.Screen.Send(test_string + "\b" * len(test_string))
                result = new_tab.Screen.WaitForStrings(test_string, response_timeout)
                if result:
                    self.logger.debug("<NEW_TAB> At prompt.  Continuing".format(result))
                    at_prompt = True

        new_session = sessions.CRTSession(self, new_tab, from_new_tab=True, prompt_endings=expanded_endings)
        if new_tab.Index == self.crt.GetScriptTab().Index:
            self.main = new_session
        # Return a new CRTSession object that can interact with this new connection
        return new_session

    def create_new_saved_session(self, session_name, ip, protocol="SSH2", folder="_imports"):
        """
        Creates a session object that can be opened from the Connect menu in SecureCRT.

        :param session_name: The name of the session
        :type session_name: str
        :param ip: The IP address or hostname of the device represented by this session
        :type ip: str
        :param protocol: The protocol to use for this connection (TELNET, SSH1, SSH2, etc)
        :type protocol: str
        :param folder: The folder (starting from the configured Sessions folder) where this session should be saved.
        :type folder: str
        """
        now = datetime.datetime.now()
        creation_date = now.strftime("%A, %B %d %Y at %H:%M:%S")

        # Create a session from the configured default values.
        new_session = self.crt.OpenSessionConfiguration("Default")

        # Set options based)
        new_session.SetOption("Protocol Name", protocol)
        new_session.SetOption("Hostname", ip)
        desc = ["Created on {} by script:".format(creation_date), self.crt.ScriptFullName]
        new_session.SetOption("Description", desc)
        session_path = os.path.join(folder, session_name)
        # Save session based on passed folder and session name.
        self.logger.debug("<CREATE_SESSION> Creating new session '{0}'".format(session_path))
        new_session.Save(session_path)


class DirectScript(Script):
    """
    This sub-class of the App class is used to wrap the portion of the SecureCRT API that interacts with the main
    application.
    """

    def __init__(self, full_script_path):
        super(DirectScript, self).__init__(full_script_path)
        self.logger.debug("<INIT> Building DirectExecution Object")
        self.main_session = sessions.DirectSession(self)

    def message_box(self, message, title="", options=0):
        """
        Prints a message for the user.  In SecureCRT, the message is displayed in a pop-up message box.  When used in a
        DirectSession, the message is printed to the console and the user is prompted to type the button that would be
        selected.

        This window can be customized by setting the "options" value, using the constants listed at the top of the
        sessions.py file.  One constant from each of the 3 categories can be OR'd (|) together to make a single option
        value that will format the message box.

        :param message: The message to send to the user
        :type message: str
        :param title: Title for the message box
        :type title: str
        :param options: Sets the display format of the messagebox. (See Message Box constants in sessions.py)
        :type options: int

        :return: The return code that identifies which button the user pressed. (See Message Box constants)
        :rtype: int
        """
        def get_button_layout(option):
            # These numbers signify default buttons and icons shown.  We don't care about these when using console.
            numbers = [512, 256, 64, 48, 32, 16]

            for number in numbers:
                if option >= number:
                    option -= number

            return option

        def get_response_code(text):
            responses = {"OK": IDOK, "Cancel": IDCANCEL, "Yes": IDYES, "No": IDNO, "Retry": IDRETRY, "Abort": IDABORT,
                         "Ignore": IDIGNORE}
            return responses[text]

        self.logger.debug("<MESSAGEBOX> Creating Message Box, with Title: {}, Message: {}, and Options: {}"
                          .format(title, message, options))
        # Extract the layout paramter in the options field
        layout = get_button_layout(options)
        self.logger.debug("<MESSAGEBOX> Layout Value is: {}".format(layout))

        # A mapping of each integer value and which buttons are shown in a MessageBox, so we can prompt for the
        # same values from the console
        buttons = {BUTTON_OK: ["OK"], BUTTON_CANCEL: ["OK", "Cancel"],
                   BUTTON_ABORTRETRYIGNORE: ["Abort", "Retry", "Ignore"],
                   BUTTON_YESNOCANCEL: ["Yes", "No", "Cancel"], BUTTON_YESNO: ["Yes", "No"],
                   BUTTON_RETRYCANCEL: ["Retry", "Cancel"]}

        print "{0}: {1}".format(message, title)
        response = ""
        while response not in buttons[layout]:
            response = raw_input("Choose from {0}: ".format(buttons[layout]))
            self.logger.debug("<MESSAGEBOX> Received: {}".format(response))

        code = get_response_code(response)
        self.logger.debug("<MESSAGEBOX> Returning Response Code: {}".format(code))
        return code

    def prompt_window(self, message, title="", hide_input=False):
        """
        Prompts the user for an input value.  In SecureCRT this will open a pop-up window where the user can input the
        requested information.  In a direct session, the user will be prompted at the console for input.

        The "hide_input" input will mask the input, so that passwords or other senstive information can be requested.

        :param message: The message to send to the user
        :type message: str
        :param title: Title for the prompt window
        :type title: str
        :param hide_input: Specifies whether to hide the user input or not.  Default is False.
        :type hide_input: bool

        :return: The value entered by the user
        :rtype: str
        """
        self.logger.debug("<PROMPT> Creating Prompt with message: '{}'".format(message))
        result = raw_input("{}: ".format(message))
        self.logger.debug("<PROMPT> Captures prompt results: '{}'".format(result))
        return result

    def file_open_dialog(self, title, button_label="Open", default_filename="", file_filter=""):
        """
        Prompts the user to select a file that will be processed by the script.  In SecureCRT this will give a pop-up
        file selection dialog window.  For a direct session, the user will be prompted for the full path to a file.
        See the SecureCRT built-in Help at Scripting > Script Objects Reference > Dialog Object for more details.

        :param title: <String> Title for the File Open dialog window (Only displays in Windows)
        :param button_label: <String> Label for the "Open" button
        :param default_filename: <String> If provided a default filename, the window will open in the parent directory
            of the file, otherwise the current working directory will be the starting directory.
        :param file_filter: <String> Specifies a filter for what type of files can be selected.  The format is:
            <Name of Filter> (*.<extension>)|*.<extension>||
            For example, a filter for CSV files would be "CSV Files (*.csv)|*.csv||" or multiple filters can be used:
            "Text Files (*.txt)|*.txt|Log File (*.log)|*.log||"

        :return: The absolute path to the file that was selected
        :rtype: str
        """
        result_filename = raw_input("{} (type {}): ".format(title, file_filter))
        return result_filename

    def ssh_in_new_tab(self, host, username, password, prompt_endings=("#", ">")):
        pass

    def create_new_saved_session(self, session_name, ip, protocol="SSH2", folder="_imports"):
        """
        Creates a session object that can be opened from the Connect menu in SecureCRT.

        :param session_name: The name of the session
        :type session_name: str
        :param ip: The IP address or hostname of the device represented by this session
        :type ip: str
        :param protocol: The protocol to use for this connection (TELNET, SSH1, SSH2, etc)
        :type protocol: str
        :param folder: The folder (starting from the configured Sessions folder) where this session should be saved.
        :type folder: str
        """
        print "Pretending to save session {} with hostname: {}, protocol: {}, under folder: {}"\
              .format(session_name, ip, protocol, folder)

