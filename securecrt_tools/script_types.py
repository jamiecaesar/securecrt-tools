"""
This module includes a collection of "session" objects that represent a SecureCRT scripting session.  These classes are
intended as a wrapper around the SecureCRT Python API to simplify common tasks that are performed against network
devices such as routers and switches.

The base class is named "Session" is the parent for more specific session types and includes all methods that must be
implemented by all sub-classes.

The primary subclass is named "CRTSession" which is specific to interacting with the Python API for SecureCRT.
Whenever a script is launched from SecureCRT, this class should be used to interact with SecureCRT.

A second subclass called "DirectSession" is used to run scripts outside of SecureCRT, such as in an IDE.  The class has
the same API as CRTSession so that no modifications are needed to run a script directly.  This is useful for debugging
because you can run your script using IDE (e.g. PyCharm, Eclipse, Spyder) debugging tools while simulating the logic of
your script.

For example, when if the "get_command_output()" method is called when executing under SecureCRT, the script will issue
the command to the remote device and save the output to a variable.  When that method is called while running directly,
the user will be prompted in the console window to supply a file location for that output.  The script will read the
file and save that output to a variable.  The logic of parsing that output is much easier to troubleshoot outside of
SecureCRT, and once the code is working working locally it should also run fine within SecureCRT.
"""

import os
import sys
import logging
import time
import datetime
import re
from abc import ABCMeta, abstractmethod
from settings import SettingsImporter
from message_box_const import *


# ################################################    EXCEPTIONS     ###################################################

class SecureCRTToolsError(Exception):
    """
    An exception type that is raised when there is a problem with the tools scripts, such as missing settings files.
    """
    pass


class ConnectError(Exception):
    """
    An exception type that is raised when there are problems connecting to a device.
    """
    pass


class InteractionError(Exception):
    """
    An exception type used when an expected response isn't received when interacting with a device.
    """
    pass


class UnsupportedOSError(Exception):
    """
    An exception type used when the remote device is running an OS that isn't supported by the script.
    """
    pass


# ################################################    SCRIPT TYPES    ##################################################


class Script:
    """
    This is a base class for the other Session types.  This class simply exists to enforce the required methods any
    sub-classes have to implement.  There are also a couple methods that are common to all sessions so they are defined
    under this class and automatically inherited by the sub-classes.
    """
    __metaclass__ = ABCMeta

    def __init__(self, script_path):
        # Initialize session variables
        self.script_dir, self.script_name = os.path.split(script_path)
        self.os = None
        self.prompt = None
        self.prompt_stack = []
        self.hostname = None
        self.term_len = None
        self.term_width = None
        self.logger = logging

        # Load Settings
        settings_file = os.path.join(self.script_dir, "settings", "settings.ini")
        try:
            self.settings = SettingsImporter(settings_file)
        except IOError:
            error_str = "A settings file at {} does not exist.  Do you want to create it?".format(settings_file)
            result = self.message_box(error_str, "Missing Settings File", ICON_QUESTION | BUTTON_YESNO)
            if result == IDYES:
                self.settings = SettingsImporter(settings_file, create=True)
            else:
                raise SecureCRTToolsError("Settings file not found")

        # Extract and store "save path" for future reference by scripts.
        output_dir = self.settings.get("Global", "output_dir")
        exp_output_dir = os.path.expandvars(os.path.expanduser(output_dir))
        if os.path.isabs(exp_output_dir):
            self.output_dir = os.path.realpath(exp_output_dir)
        else:
            full_path = os.path.join(self.script_dir, exp_output_dir)
            self.output_dir = os.path.realpath(full_path)
        self.validate_dir(self.output_dir)

        # Save date and time of launch to use in file names
        now = datetime.datetime.now()
        date_format = self.settings.get("Global", "date_format")
        self.datetime = now.strftime(date_format)
        self.logger.debug("<INIT> Saved script launch time as: {}".format(self.datetime))

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
            self.logger.debug("<INIT> Starting Logging. Running Python version: {0}".format(sys.version))

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

    def create_output_filename(self, desc, ext=".txt", include_hostname=True, include_date=True, base_dir=None):
        """
        Generates a filename (including absoluate path) based on details from the session.

        :param desc: A short description to include in the filename (i.e. "show run", "cdp", etc)
        :type desc: str
        :param base_dir: (Optional) The director where this file should be saved. Default: SavePath from settings.
        :type base_dir: str
        :param ext: (Optional) Extension for the filename.  Default: ".txt"
        :type ext: str
        :param include_date: (Optional) Include a timestamp in the filename.  The timestamp format is taken from the
            settings file.  Default: True
        :type include_date: bool

        :return: The generated absolute path for the filename requested.
        :rtype: str
        """

        self.logger.debug("<CREATE_FILENAME> Starting creation of filename with Desc: {}, Base Dir: {}, ext: {}, "
                          "include_date: {}".format(desc, base_dir, ext, include_date))

        if base_dir:
            save_path = os.path.realpath(base_dir)
        else:
            save_path = self.output_dir

        self.logger.debug("<CREATE_FILENAME> Save Location: {0}".format(save_path))

        # Remove reserved filename characters from filename
        clean_desc = desc.replace("/", "-")
        clean_desc = clean_desc.replace(".", "-")
        clean_desc = clean_desc.replace(":", "-")
        clean_desc = clean_desc.replace("\\", "")
        clean_desc = clean_desc.replace("| ", "")
        # Just in case the trailing space from the above replacement was missing.
        clean_desc = clean_desc.replace("|", "")

        if include_hostname:
            self.logger.debug("<CREATE_FILENAME> Using hostname.")
            hostname = self.hostname
        else:
            self.logger.debug("<CREATE_FILENAME> NOT using hostname.")
            hostname = ""

        if include_date:
            # Get the current date in the format supplied in date_format
            my_date = self.datetime
        else:
            self.logger.debug("<CREATE_FILENAME> Not including date.")
            my_date = ""

        file_bits = [hostname, clean_desc, my_date]
        self.logger.debug("<CREATE_FILENAME> Using {} to create filename".format(file_bits))
        # Create filename, stripping off leading or trailing "-" if some fields are not used.
        filename = '-'.join(file_bits).strip("-")
        # If ext starts with a '.', add it, otherwise put the '.' in there ourselves.
        if ext[0] == '.':
            filename = filename + ext
        else:
            filename = "{}.{}".format(filename, ext)
        file_path = os.path.join(save_path, filename)
        self.logger.debug("<CREATE_FILENAME> Final Filename: {}".format(file_path))

        return file_path

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
    def is_connected(self):
        """
        Returns a boolean value that describes if the session is currently connected.

        :return: True if the session is connected, False if not.
        :rtype: bool
        """
        pass

    @abstractmethod
    def connect_ssh(self, host, username, password, version=None, prompt_endings=("#", ">")):
        """
        Connects to a device via the SSH protocol. By default, SSH2 will be tried first, but if it fails it will attempt
        to fall back to SSH1.

        :param host: The IP address of DNS name for the device to connect
        :type host: str
        :param username: The username to login to the device with
        :type username: str
        :param password: The password that goes with the provided username.  If a password is not specified, the
            user will be prompted for one.
        :type password: str
        :param version: The SSH version to connect with (1 or 2).  Default is None, which will try 2 first and fallback
            to 1 if that fails.
        :type version: int
        :param prompt_endings: A list of strings that are possible prompt endings to watch for.  The default is for
                               Cisco devices (">" and "#"), but may need to be changed if connecting to another
                               type of device (for example "$" for some linux hosts).
        :type prompt_endings: list
        """
        pass

    @abstractmethod
    def connect_telnet(self, host, username, password, prompt_endings=("#", ">")):
        """
        Connects to a device via the Telnet protocol.

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
    def disconnect(self, command="exit"):
        """
        Disconnects the connected session by sending the "exit" command to the remote device.  If that does not make
        the disconnect happen, attempt to force and ungraceful disconnect.

        :param command: The command to be issued to the remote device to disconnect.  The default is 'exit'
        :type command: str
        """
        pass

    @abstractmethod
    def ssh_via_jump(self, host, username, password, options="-o StrictHostKeyChecking=no"):
        """
        From the connected session, this method issues the SSH command to connect to another box, using the main
        connected sessions as a jump point to reach the target.  In other words, connect_ssh() would be used to connect
        to the jump box/bastion host and then this method would be used to connect to the remote device via the jump
        host.

        If this method doesn't receive the expected prompts after issuing the credentials, an exception will be raised.

        :param host: IP address or hostname (resolvable on the jumpbox)
        :type host: str
        :param username: Username to log into the remote device with
        :type username: str
        :param password: Password for logging into the remote device
        :type password: str
        :param options: Additional "ssh" command paramters.  Default disables strict host key checking so that the
                        script will not be prompted to accept the remote key.
        :type options: str
        """
        pass

    @abstractmethod
    def telnet_via_jump(self, host, username, password):
        """
        From the connected session, this method issues the telnet command to connect to another box, using the main
        connected sessions as a jump point to reach the target.  In other words, connect_ssh() would be used to connect
        to the jump box/bastion host and then this method would be used to connect to the remote device via the jump
        host.

        If this method doesn't receive the expected prompts after issuing the credentials, an exception will be raised.

        :param host: IP address or hostname (resolvable on the jumpbox)
        :type host: str
        :param username: Username to log into the remote device with
        :type username: str
        :param password: Password for logging into the remote device
        :type password: str
        """
        pass

    @abstractmethod
    def disconnect_via_jump(self, command="exit"):
        """
        Issues a command to disconnect from the remote device, bringing us back to the jump host.  The default command
        is "exit", but it can be changed by passing in a different "command".  If we don't see the prompt for the jump
        host after issuing the disconnect command, an exception will be raised.

        :param command: The command to be issued to the remote device to disconnect.  The default is 'exit'
        :type command: str
        """
        pass

    @abstractmethod
    def start_cisco_session(self, enable_pass=None):
        """
        Performs initial setup of the session to a Cisco device by detecting parameters (prompt, hostname, network OS,
        etc) of the connected device and modifying the terminal length if configured to do so in the settings file.

        If the device is not at an enable prompt and an enable password is supplied, then this method will also enter
        enable mode on the device before proceeding.

        This should always be called before trying to interact with a Cisco device so that the majority of other
        methods will work correctly.  This should be one of the first calls in a script that is intended to run when
        already connected to the device, or called right after connecting to a device with the "connect_ssh" or similar
        method.

        :param enable_pass: The enable password that should be sent if the device is not in enable mode.
        :type enable_pass: str
        """
        pass

    @abstractmethod
    def end_cisco_session(self):
        """
        End the session by returning the device's terminal parameters that were modified by start_session() to their
        previous values.

        This should always be called before a disconnect (assuming that start_cisco_session was called after connect)
        """
        pass

    @abstractmethod
    def write_output_to_file(self, command, filename):
        """
        Send the supplied command to the remote device and writes the output to a file.

        This function was written specifically to write output line by line because storing large outputs into a
        variable will cause SecureCRT to bog down until it freezes.  A good example is a large "show tech" output.
        This method can handle any length of output

        :param command: The command to be sent to the device
        :type command: str
        :param filename: A string with the absolute path to the filename to be written.
        :type filename: str
        """
        pass

    @abstractmethod
    def get_command_output(self, command):
        """
        Captures the output from the provided command and saves the results in a variable.

        ** NOTE ** Assigning the output directly to a variable causes problems with SecureCRT for long outputs.  It
        will gradually get slower and slower until the program freezes and crashes.  The workaround is to
        save the output directly to a file (line by line), and then read it back into a variable.  This is the
        procedure that this method uses.

        Keyword Arguments:
            :param command: Command string that should be sent to the device
            :type command: str

        :return: The result from issuing the above command.
        :rtype: str
        """
        pass

    @abstractmethod
    def send_config_commands(self, command_list, output_filename=None):
        """
        This method accepts a list of strings, where each string is a command to be sent to the device.

        This method will send "conf t", then all the commands from the list and finally send "end" to the device.
        If an output_filenameThe results returned from entering the commands into the device are written to a file.

        NOTE: This method is new and does not have any error checking for how the remote device handles the commands
        you are trying to send.  USE IT AT YOUR OWN RISK.

        :param command_list: A list of strings, where each string is a command to be sent.  This should NOT include
                            'config t' or 'end'.  This is added automatically.
        :type command_list: list
        :param output_filename: (Optional) If a absolute path to a file is specified, the config session output from
                                applying the commands will be written to this file.
        :type output_filename: str
        """
        pass

    @abstractmethod
    def save(self, command="copy running-config startup-config"):
        """
        Sends a "copy running-config startup-config" command to the remote device to save the running configuration.
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
    This sub-class of the Session class is used to wrap the SecureCRT API to simplify writing new scripts.  This class
    includes some private methods thare are used to support the interaction with SecureCRT (these start with '__').
    """

    def __init__(self, crt):
        self.crt = crt
        super(CRTScript, self).__init__(crt.ScriptFullName)
        self.logger.debug("<INIT> Starting creation of CRTSession object")
        self.response_timeout = 10
        self.session_set_sync = False

        # Set up SecureCRT tab for interaction with the scripts
        self.tab = self.crt.GetScriptTab().Screen

        if not self.is_connected():
            self.logger.debug("<INIT> Session not connected prior to creating object.  Skipping device setup.")
        else:
            self.logger.debug("<INIT> Session already connected.  Moving on.")

    def __send(self, command):
        if self.is_connected():
            self.tab.Send(command)
            result = self.tab.WaitForString(command.strip(), self.response_timeout)
            if not result:
                self.logger.debug("<__send> Timed out waiting for '{}' from device.".format(command))
                raise InteractionError("Timed out waiting for sent command to be echoed back to us.")
            else:
                return result
        else:
            self.logger.debug("<__send> Not connected. Error.".format(command))
            raise InteractionError("Session is not connected.  Cannot send command.")

    def __wait_for_string(self, wait_string):
        result = self.tab.WaitForString(wait_string, self.response_timeout)
        if not result:
            self.logger.debug("<__wait_for_string> Timed out waiting for '{}' from device.".format(wait_string))
            raise InteractionError("Timeout waiting for response from device.")
        else:
            return result

    def __wait_for_strings(self, string_list):
        result = self.tab.WaitForStrings(string_list, self.response_timeout)
        if not result:
            self.logger.debug("<__wait_for_strings> Timed out waiting for '{}' from device.".format(string_list))
            raise InteractionError("Timeout waiting for response from device.")
        else:
            return result

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

    def is_connected(self):
        """
        Returns a boolean value that describes if the session is currently connected.

        :return: True if the session is connected, False if not.
        :rtype: bool
        """
        session_connected = self.crt.Session.Connected
        if session_connected == 1:
            self.logger.debug("<IS_CONNECTED> Checking Connected Status.  Got: {} (True)".format(session_connected))
            return True
        else:
            self.logger.debug("<IS_CONNECTED> Checking Connected Status.  Got: {} (False)".format(session_connected))
            return False

    def __post_connect_check(self, endings):
        """
        Validates that we've gotten to the prompt after a connection is made.

        :param endings: A list of strings, where each string is a possible character that would be found at the end
                        of the CLI prompt for the remote device.
        :type endings: list
        """
        self.logger.debug("<CONN_CHECK> Started looking for following prompt endings: {}".format(endings))
        at_prompt = False
        while not at_prompt:
            found = self.tab.WaitForStrings(endings, self.response_timeout)
            if not found:
                raise InteractionError("Timeout reached looking for prompt endings: {}".format(endings))
            else:
                test_string = "!@&^"
                self.tab.Send(test_string + "\b" * len(test_string))
                result = self.tab.WaitForStrings(test_string, self.response_timeout)
                if result:
                    self.logger.debug("<CONN_CHECK> At prompt.  Continuing".format(result))
                    at_prompt = True

    def __connect_ssh_2(self, host, username, password, prompt_endings=("#", "# ", ">")):
        if not prompt_endings:
            raise ConnectError("Cannot connect without knowing what character ends the CLI prompt.")

        expanded_endings = []
        for ending in prompt_endings:
            expanded_endings.append("{}".format(ending))
            expanded_endings.append("{} ".format(ending))

        ssh2_string = "/SSH2 /ACCEPTHOSTKEYS /L {} /PASSWORD {} {}".format(username, password, host)
        # If the tab is already connected, then give an exception that we cannot connect.
        if self.is_connected():
            self.logger.debug("<CONNECT_SSH2> Session already connected.  Raising exception")
            raise ConnectError("Tab is already connected to another device.")
        else:
            try:
                self.logger.debug("<CONNECT_SSH2> Attempting Connection to: {}@{} via SSH2".format(username, host))
                self.crt.Session.Connect(ssh2_string)
            except:
                error = self.crt.GetLastErrorMessage()
                raise ConnectError(error)

        # Set Tab parameters to allow correct sending/receiving of data via SecureCRT
        self.tab.Synchronous = True
        self.tab.IgnoreEscape = True
        self.logger.debug("<CONNECT_SSH2> Set Synchronous and IgnoreEscape")

        # Make sure banners have printed and we've reached our expected prompt.
        self.__post_connect_check(expanded_endings)

    def __connect_ssh_1(self, host, username, password, prompt_endings=("#", "# ", ">")):
        if not prompt_endings:
            raise ConnectError("Cannot connect without knowing what character ends the CLI prompt.")

        expanded_endings = []
        for ending in prompt_endings:
            expanded_endings.append("{}".format(ending))
            expanded_endings.append("{} ".format(ending))

        ssh1_string = "/SSH1 /ACCEPTHOSTKEYS /L {} /PASSWORD {} {}".format(username, password, host)
        # If the tab is already connected, then give an exception that we cannot connect.
        if self.is_connected():
            self.logger.debug("<CONNECT_SSH1> Session already connected.  Raising exception")
            raise ConnectError("Tab is already connected to another device.")
        else:
            try:
                self.logger.debug("<CONNECT_SSH1> Attempting Connection to: {}@{} via SSH1".format(username, host))
                self.crt.Session.Connect(ssh1_string)
            except:
                error = self.crt.GetLastErrorMessage()
                raise ConnectError(error)

        # Set Tab parameters to allow correct sending/receiving of data via SecureCRT
        self.tab.Synchronous = True
        self.tab.IgnoreEscape = True
        self.logger.debug("<CONNECT_SSH1> Set Synchronous and IgnoreEscape")

        # Make sure banners have printed and we've reached our expected prompt.
        self.__post_connect_check(expanded_endings)

    def connect_ssh(self, host, username, password, version=None, prompt_endings=("#", ">")):
        """
        Connects to a device via the SSH protocol. By default, SSH2 will be tried first, but if it fails it will attempt
        to fall back to SSH1.

        :param host: The IP address of DNS name for the device to connect
        :type host: str
        :param username: The username to login to the device with
        :type username: str
        :param password: The password that goes with the provided username.  If a password is not specified, the
            user will be prompted for one.
        :type password: str
        :param version: The SSH version to connect with (1 or 2).  Default is None, which will try 2 first and fallback
            to 1 if that fails.
        :type version: int
        :param prompt_endings: A list of strings that are possible prompt endings to watch for.  The default is for
                               Cisco devices (">" and "#"), but may need to be changed if connecting to another
                               type of device (for example "$" for some linux hosts).
        :type prompt_endings: list
        """
        self.logger.debug("<CONNECT_SSH> Attempting Connection to: {}@{}".format(username, host))

        if not prompt_endings:
            raise ConnectError("Cannot connect without knowing what character ends the CLI prompt.")

        if version == 2:
            self.__connect_ssh_2(host, username, password, prompt_endings)
        elif version == 1:
            self.__connect_ssh_1(host, username, password, prompt_endings)
        else:
            try:
                self.__connect_ssh_2(host, username, password, prompt_endings)
            except ConnectError as e:
                self.logger.debug("<CONNECT_SSH> Failure trying SSH2: {}".format(e.message))
                ssh2_error = e.message
                try:
                    self.__connect_ssh_1(host, username, password, prompt_endings)
                except ConnectError as e:
                    ssh1_error = e.message
                    self.logger.debug("<CONNECT_SSH> Failure trying SSH1: {}".format(e.message))
                    error = "SSH2 and SSH1 failed.\nSSH2 Failure:{}\nSSH1 Failure:{}".format(ssh2_error, ssh1_error)
                    raise ConnectError(error)

    def connect_telnet(self, host, username, password, prompt_endings=("#", ">")):
        """
        Connects to a device via the Telent protocol.

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
        if not prompt_endings:
            raise ConnectError("Cannot connect without knowing what character ends the CLI prompt.")

        telnet_string = "/TELNET {}".format(host)
        # If the tab is already connected, then give an exception that we cannot connect.
        if self.is_connected():
            self.logger.debug("<CONNECT_TELNET> Session already connected.  Raising exception")
            raise ConnectError("Tab is already connected to another device.")
        else:
            try:
                self.logger.debug("<CONNECT_TELNET> Attempting Connection to: {} via TELNET".format(host))
                self.crt.Session.Connect(telnet_string)
            except:
                error = self.crt.GetLastErrorMessage()
                raise ConnectError(error)

        # Set Tab parameters to allow correct sending/receiving of data via SecureCRT
        self.tab.Synchronous = True
        self.tab.IgnoreEscape = True
        self.logger.debug("<CONNECT_TELNET> Set Synchronous and IgnoreEscape")

        # Handle Login
        self.__wait_for_strings("sername")
        self.__send("{}\n".format(username))
        self.__wait_for_string("assword")
        self.tab.Send("{}\n".format(password))

        # Make sure banners have printed and we've reached our expected prompt.
        self.__post_connect_check(prompt_endings)

    def disconnect(self, command="exit"):
        """
        Disconnects the connected session by sending the "exit" command to the remote device.  If that does not make
        the disconnect happen, attempt to force and ungraceful disconnect.

        :param command: The command to be issued to the remote device to disconnect.  The default is 'exit'
        :type command: str
        """
        self.logger.debug("<DISCONNECT> Sending '{}' command.".format(command))
        self.__send("{}\n".format(command))

        # Unset Sync and IgnoreEscape upon disconnect
        self.tab.Synchronous = False
        self.tab.IgnoreEscape = False

        # Give a little time and check if we are disconnected.  If not, force it.
        time.sleep(0.25)
        attempts = 0
        while self.is_connected() and attempts < 10:
            self.logger.debug("<DISCONNECT> Not disconnected.  Attempting ungraceful disconnect.")
            self.crt.Session.Disconnect()
            time.sleep(0.1)
            attempts += 1
        if attempts >= 10:
            raise ConnectError("Unable to disconnect from session.")

    def ssh_via_jump(self, host, username, password, options="-o StrictHostKeyChecking=no", prompt_endings=("#", ">")):
        """
        From the connected session, this method issues the SSH command to connect to another box, using the main
        connected sessions as a jump point to reach the target.  In other words, connect_ssh() would be used to connect
        to the jump box/bastion host and then this method would be used to connect to the remote device via the jump
        host.

        If this method doesn't receive the expected prompts after issuing the credentials, an exception will be raised.

        :param host: IP address or hostname (resolvable on the jumpbox)
        :type host: str
        :param username: Username to log into the remote device with
        :type username: str
        :param password: Password for logging into the remote device
        :type password: str
        :param options: Additional "ssh" command paramters.  Default disables strict host key checking so that the
                        script will not be prompted to accept the remote key.
        :type options: str
        """
        if not self.prompt:
            self.prompt = self.__get_prompt()
        self.__send("ssh {} {}@{}\n".format(options, username, host))
        result = self.__wait_for_strings(["assword", "refused", "denied"])
        if result == 1:
            self.tab.Send("{}\n".format(password))
            self.__post_connect_check(prompt_endings)
            self.prompt_stack.insert(0, self.prompt)
        else:
            raise ConnectError("SSH connection refused.")

    def telnet_via_jump(self, host, username, password, prompt_endings=("#", ">")):
        """
        From the connected session, this method issues the telnet command to connect to another box, using the main
        connected sessions as a jump point to reach the target.  In other words, connect_ssh() would be used to connect
        to the jump box/bastion host and then this method would be used to connect to the remote device via the jump
        host.

        If this method doesn't receive the expected prompts after issuing the credentials, an exception will be raised.

        :param host: IP address or hostname (resolvable on the jumpbox)
        :type host: str
        :param username: Username to log into the remote device with
        :type username: str
        :param password: Password for logging into the remote device
        :type password: str
        """
        if not self.prompt:
            self.prompt = self.__get_prompt()
        self.__send("telnet {}\n".format(host))
        result = self.__wait_for_strings(["sername", "refused", "denied"])
        if result == 1:
            self.__send("{}\n".format(username))
            self.__wait_for_string("assword")
            self.tab.Send("{}\n".format(password))
            self.__post_connect_check(prompt_endings)
            self.prompt_stack.insert(0, self.prompt)
        else:
            raise ConnectError("Telnet connection refused.")

    def disconnect_via_jump(self, command="exit"):
        """
        Issues a command to disconnect from the remote device, bringing us back to the jump host.  The default command
        is "exit", but it can be changed by passing in a different "command".  If we don't see the prompt for the jump
        host after issuing the disconnect command, an exception will be raised.

        :param command: The command to be issued to the remote device to disconnect.  The default is 'exit'
        :type command: str
        """
        try:
            prev_prompt = self.prompt_stack.pop(0)
        except IndexError:
            prev_prompt = None
        self.__send("{}\n".format(command))
        self.__wait_for_string(prev_prompt)

    def start_cisco_session(self, enable_pass=None):
        """
        Performs initial setup of the session to a Cisco device by detecting parameters (prompt, hostname, network OS,
        etc) of the connected device and modifying the terminal length if configured to do so in the settings file.

        If the device is not at an enable prompt and an enable password is supplied, then this method will also enter
        enable mode on the device before proceeding.

        This should always be called before trying to interact with a Cisco device so that the majority of other
        methods will work correctly.  This should be one of the first calls in a script that is intended to run when
        already connected to the device, or called right after connecting to a device with the "connect_ssh" or similar
        method.

        :param enable_pass: The enable password that should be sent if the device is not in enable mode.
        :type enable_pass: str
        """
        # Validate we are connected before trying to start a Cisco session
        if not self.is_connected():
            raise InteractionError("Session is not connected.  Cannot start Cisco session.")

        prompt_for_enable = False
        # Set Tab parameters to allow correct sending/receiving of data via SecureCRT, if manually connected session
        # (i.e. it hasn't been set yet)
        if not self.tab.Synchronous:
            self.session_set_sync = True
            self.tab.Synchronous = True
            self.tab.IgnoreEscape = True
            prompt_for_enable = True
            self.logger.debug("<START> Set Synchronous and IgnoreEscape and Prompt For Enable")

        # Get prompt (and thus hostname) from device
        self.prompt = self.__get_prompt()
        self.__enter_enable(enable_pass, prompt_for_enable)
        self.hostname = self.prompt[:-1]
        self.logger.debug("<START> Set Hostname: {}".format(self.hostname))

        # Detect the OS of the device, because outputs will differ per OS
        self.os = self.__get_network_os()
        self.logger.debug("<START> Discovered OS: {}".format(self.os))

        # Get terminal length and width, so we can revert back after changing them.
        self.term_len, self.term_width = self.__get_term_info()
        self.logger.debug("<START> Discovered Term Len: {}, Term Width: {}".format(self.term_len, self.term_width))

        # If modify_term setting is True, then prevent "--More--" prompt (length) and wrapping of lines (width)
        if self.settings.getboolean("Global", "modify_term"):
            self.logger.debug("<START> Modify Term setting is set.  Sending commands to adjust terminal")
            if self.os == "IOS" or self.os == "NXOS":
                # Send term length command and wait for prompt to return
                if self.term_len:
                    self.__send('term length 0\n')
                    self.__wait_for_string(self.prompt)
            elif self.os == "ASA":
                if self.term_len:
                    self.__send('terminal pager 0\r\n')
                    self.__wait_for_string(self.prompt)

            # Send term width command and wait for prompt to return (depending on platform)

            if self.os == "IOS":
                if self.term_len:
                    self.__send('term width 0\n')
                    self.__wait_for_string(self.prompt)
            elif self.os == "NXOS":
                if self.term_len:
                    self.__send('term width 511\n')
                    self.__wait_for_string(self.prompt)

        # Added due to Nexus echoing twice if system hangs and hasn't printed the prompt yet.
        # Seems like maybe the previous WaitFor prompt isn't always working correctly.  Something to look into.
        time.sleep(0.1)

    def end_cisco_session(self):
        """
        End the session by returning the device's terminal parameters that were modified by start_session() to their
        previous values.

        This should always be called before a disconnect (assuming that start_cisco_session was called after connect)
        """

        # If the 'tab' and 'prompt' options aren't in the session structure, then we aren't actually connected to a
        # device when this is called, and there is nothing to do.
        self.logger.debug("<END> Ending Session")
        if self.crt:
            if self.tab:
                if self.prompt:
                    if self.settings.getboolean("Global", "modify_term"):
                        self.logger.debug("<END> Modify Term setting is set.  Sending commands to return terminal "
                                          "to normal.")
                        if self.os == "IOS" or self.os == "NXOS":
                            if self.term_len:
                                # Set term length back to saved values
                                self.__send('term length {}\n'.format(self.term_len))
                                self.__wait_for_string(self.prompt)

                            if self.term_width:
                                # Set term width back to saved values
                                self.__send('term width {}\n'.format(self.term_width))
                                self.__wait_for_string(self.prompt)
                        elif self.os == "ASA":
                            self.tab.Send("terminal pager {}\n".format(self.term_len))

                self.prompt = None
                self.logger.debug("<END> Deleting learned Prompt.")
                self.hostname = None
                self.logger.debug("<END> Deleting learned Hostname.")

                # Delete the detected OS
                self.os = None
                self.logger.debug("<END> Deleting Discovered OS.")

                # Return SecureCRT Synchronous and IngoreEscape values back to defaults, if needed.
                if self.session_set_sync:
                    self.tab.Synchronous = False
                    self.tab.IgnoreEscape = False
                    self.session_set_sync = False
                    self.logger.debug("<END> Unset Synchronous and IgnoreEscape")

    def __enter_enable(self, enable_pass, prompt=False):
        """
        A function that will attempt to enter enable mode, if we aren't in enable mode when the method is called.

        :param enable_pass: The enable password to use for the connected device.
        :type enable_pass: str
        """
        if self.prompt[-1] == "#":
            self.logger.debug("<__enter_enable> Already in enable -- Moving on.")
        elif self.prompt[-1] == ">":
            if not enable_pass and prompt:
                enable_pass = self.prompt_window("Please enter enable password.", "Enter Enable PW", hide_input=True)
            if enable_pass:
                self.logger.debug("<__enter_enable> Not in enable.  Attempting to elevate privilege.")
                self.__send("enable\n")
                result = self.__wait_for_strings(["% No", "assword", ">"])
                if result == 1:
                    self.logger.debug("<__enter_enable> Enable password not set.")
                    raise InteractionError("Unable to enter Enable mode. No password set.")
                if result == 2:
                    self.tab.Send("{}\n".format(enable_pass))
                    self.__wait_for_string("#")
                    self.prompt = self.__get_prompt()
                else:
                    self.logger.debug("<__enter_enable> Failed to detect password prompt after issuing 'enable'.")
                    raise InteractionError("Unable to enter Enable mode.")
            else:
                self.logger.debug("<__enter_enable> Not in enable mode and no enable password given.  Cannot proceed.")
                raise InteractionError("Not in enable mode and no enable password given.  Cannot proceed.")
        else:
            self.logger.debug("<__enter_enable> Unable to recognize Cisco style prompt.")
            raise InteractionError("Unable to recognize Cisco style prompt")

    def __get_prompt(self):
        """
        Discovers the prompt of the remote device and returns it.
        """
        self.logger.debug("<GET PROMPT> Attempting to discover device prompt.")

        result = ''
        attempts = 0
        while result == '' and attempts < 3:
            test_string = "\n!&%\b\b\b"
            timeout_seconds = 2
            self.tab.Send(test_string)
            result = self.tab.ReadString("!&%", timeout_seconds)
            attempts += 1
            self.logger.debug("<CONNECT> Attempt {}: Prompt result = {}".format(attempts, result))

        prompt = result.strip(u"\r\n\b ")
        if prompt == '':
            self.logger.debug("<GET PROMPT> Prompt discovery failed.  Raising exception.")
            raise InteractionError("Unable to discover device prompt")

        self.logger.debug("<GET PROMPT> Discovered prompt as '{}'.".format(prompt))
        return prompt

    def __get_network_os(self):
        """
        Discovers Network OS type so that scripts can make decisions based on the information, such as sending a
        different version of a command for a particular OS.
        """
        send_cmd = "show version | i Cisco"

        raw_version = self.__get_output(send_cmd)
        self.logger.debug("<GET OS> Version String: {0}".format(raw_version))

        if "IOS XE" in raw_version:
            version = "IOS"
        elif "Cisco IOS Software" in raw_version or "Cisco Internetwork Operating System" in raw_version:
            version = "IOS"
        elif "Cisco Nexus Operating System" in raw_version:
            version = "NXOS"
        elif "Adaptive Security Appliance" in raw_version:
            version = "ASA"
        else:
            self.logger.debug("<GET OS> Error detecting OS.  Raising Exception.")
            raise InteractionError("Unknown or Unsupported device OS.")

        return version

    def __get_term_info(self):
        """
        Returns the current terminal length and width, by capturing the output from the relevant commands.

        :return: A 2-tuple containing the terminal length and the terminal width
        """
        re_num_exp = r'\d+'
        re_num = re.compile(re_num_exp)

        if self.os == "IOS" or self.os == "NXOS":
            result = self.__get_output("show terminal | i Length")
            term_info = result.split(',')

            re_length = re_num.search(term_info[0])
            if re_length:
                length = re_length.group(0)
            else:
                length = None

            re_width = re_num.search(term_info[1])
            if re_width:
                width = re_width.group(0)
            else:
                width = None

            return length, width

        elif self.os == "ASA":
            pager = self.__get_output("show pager")
            re_length = re_num.search(pager)
            if re_length:
                length = re_length.group(0)
            else:
                length = None

            term_info = self.__get_output("show terminal")
            re_width = re_num.search(term_info[1])
            if re_width:
                width = re_width.group(0)
            else:
                width = None

            return length, width

        else:
            return None, None

    def __get_output(self, command):
        """
        A function that issues a command to the current session and returns the output as a string variable.
        *** NOTE *** This is  a private method because it should only be used when it is guaranteed that the output
        will be small (less than 1000 lines), or else SecureCRT can bog down and crash.  "get_command_output()" is safer
        because it avoids the problem by writing the output to a file before reading it back into a variable.

        :param command: Command string that should be sent to the device
        :type command: str

        Variable holding the result of issuing the above command.
        """
        # Send command
        self.__send(command.strip() + '\n')

        # Capture the output until we get our prompt back and write it to the file
        result = self.tab.ReadString(self.prompt)

        return result.strip('\r\n')

    def write_output_to_file(self, command, filename):
        """
        Send the supplied command to the remote device and writes the output to a file.

        This function was written specifically to write output line by line because storing large outputs into a
        variable will cause SecureCRT to bog down until it freezes.  A good example is a large "show tech" output.
        This method can handle any length of output

        :param command: The command to be sent to the device
        :type command: str
        :param filename: A string with the absolute path to the filename to be written.
        :type filename: str
        """
        self.logger.debug("<WRITE_FILE> Call to write_output_to_file with command: {}, filename: {}"
                          .format(command, filename))
        self.validate_dir(os.path.dirname(filename))
        self.logger.debug("<WRITE_FILE> Using filename: {0}".format(filename))

        # RegEx to match the whitespace and backspace commands after --More-- prompt
        exp_more = r' [\b]+[ ]+[\b]+(?P<line>.*)'
        re_more = re.compile(exp_more)

        # The 3 different types of lines we want to match (MatchIndex) and treat differntly
        if self.os == "IOS" or self.os == "NXOS":
            matches = ["\r\n", '--More--', self.prompt]
        elif self.os == "ASA":
            matches = ["\r\n", '<--- More --->', self.prompt]
        else:
            matches = ["\r\n", '--More--', self.prompt]

        # Write the output to the specified file
        try:
            # Need the 'b' in mode 'wb', or else Windows systems add extra blank lines.
            with open(filename, 'wb') as newfile:
                self.__send(command + "\n")

                # Loop to capture every line of the command.  If we get CRLF (first entry in our "endings" list), then
                # write that line to the file.  If we get our prompt back (which won't have CRLF), break the loop b/c we
                # found the end of the output.
                while True:
                    nextline = self.tab.ReadString(matches, 30)
                    # If the match was the 1st index in the endings list -> \r\n
                    if self.tab.MatchIndex == 1:
                        # Strip newlines from front and back of line.
                        nextline = nextline.strip('\r\n')
                        # If there is something left, write it.
                        if nextline != "":
                            # Check for backspace and spaces after --More-- prompt and strip them out if needed.
                            regex = re_more.match(nextline)
                            if regex:
                                nextline = regex.group('line')
                            # Strip line endings from line.  Also re-encode line as ASCII
                            # and ignore the character if it can't be done (rare error on
                            # Nexus)
                            newfile.write(nextline.strip('\r\n').encode('ascii', 'ignore') + "\r\n")
                            self.logger.debug("<WRITE_FILE> Writing Line: {0}".format(nextline.strip('\r\n')
                                                                                      .encode('ascii', 'ignore')))
                    elif self.tab.MatchIndex == 2:
                        # If we get a --More-- send a space character
                        self.tab.Send(" ")
                    elif self.tab.MatchIndex == 3:
                        # We got our prompt, so break the loop
                        break
                    else:
                        raise InteractionError("Timeout trying to capture output")

        except IOError, err:
            error_str = "IO Error for:\n{0}\n\n{1}".format(filename, err)
            self.message_box(error_str, "IO Error", ICON_STOP)

    def get_command_output(self, command):
        """
        Captures the output from the provided command and saves the results in a variable.

        ** NOTE ** Assigning the output directly to a variable causes problems with SecureCRT for long outputs.  It
        will gradually get slower and slower until the program freezes and crashes.  The workaround is to
        save the output directly to a file (line by line), and then read it back into a variable.  This is the
        procedure that this method uses.

        Keyword Arguments:
            :param command: Command string that should be sent to the device
            :type command: str

        :return: The result from issuing the above command.
        :rtype: str
        """
        self.logger.debug("<GET OUTPUT> Running get_command_output with input '{0}'".format(command))

        # Create a temporary filename
        temp_filename = self.create_output_filename("{0}-temp".format(command))
        self.logger.debug("<GET OUTPUT> Temp Filename".format(temp_filename))

        self.write_output_to_file(command, temp_filename)

        with open(temp_filename, 'r') as temp_file:
            result = temp_file.read()

        # If debug mode is enabled, save temporary file to the debug directory.
        if self.settings.getboolean("Global", "debug_mode"):
            filename = os.path.split(temp_filename)[1]
            new_filename = os.path.join(self.debug_dir, filename)
            self.logger.debug("<GET OUTPUT> Moving temp file to {0}".format(new_filename))
            os.rename(temp_filename, new_filename)
        else:
            self.logger.debug("<GET OUTPUT> Deleting {0}".format(temp_filename))
            os.remove(temp_filename)
        self.logger.debug("<GET OUTPUT> Returning results of size {0}".format(sys.getsizeof(result)))
        return result

    def send_config_commands(self, command_list, output_filename=None):
        """
        This method accepts a list of strings, where each string is a command to be sent to the device.

        This method will send "conf t", then all the commands from the list and finally send "end" to the device.
        If an output_filenameThe results returned from entering the commands into the device are written to a file.

        NOTE: This method is new and does not have any error checking for how the remote device handles the commands
        you are trying to send.  USE IT AT YOUR OWN RISK.

        :param command_list: A list of strings, where each string is a command to be sent.  This should NOT include
                            'config t' or 'end'.  This is added automatically.
        :type command_list: list
        :param output_filename: (Optional) If a absolute path to a file is specified, the config session output from
                                applying the commands will be written to this file.
        :type output_filename: str
        """
        self.logger.debug("<SEND_CMDS> Preparing to write commands to device.")
        self.logger.debug("<SEND_CMDS> Received: {}".format(str(command_list)))

        # Build text commands to send to device, and book-end with "conf t" and "end"
        config_results = ""
        command_list.insert(0, "configure terminal")

        for command in command_list:
            self.tab.Send("{}\n".format(command))
            output = self.tab.ReadString(")#", 3)
            if output:
                config_results += "{})#".format(output)
            else:
                error = "Did not receive expected prompt after issuing command: {}".format(command)
                self.logger.debug("<SEND_CMDS> {}".format(error))
                raise InteractionError("{}".format(error))

        self.tab.Send("end\n")
        output = self.tab.ReadString(self.prompt, 2)
        config_results += "{}{}".format(output, self.prompt)

        with open(output_filename, 'w') as output_file:
            self.logger.debug("<SEND_CMDS> Writing config session output to: {}".format(output_filename))
            output_file.write(config_results.replace("\r", ""))

    def save(self, command="copy running-config startup-config"):
        """
        Sends a "copy running-config startup-config" command to the remote device to save the running configuration.
        """
        self.logger.debug("<SAVE> Saving configuration on remote device.")
        self.__send("{}\n".format(command))
        save_results = self.__wait_for_strings(["?", self.prompt])
        if save_results == 1:
            self.tab.Send("\n")
        self.logger.debug("<SAVE> Save results: {}".format(save_results))

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
    This class is used when the scripts are executed directly from a local Python installation instead of from
    SecureCRT.  This class is intended to simulate connectivity to remote devices by prompting the user for what would
    otherwise be extracted from SecureCRT.  For example, when this class tries to get the output from a show command,
    it will instead prompt the user for a location of a file with the associated output.  This allows the scripts to
    be run directly in an IDE for developement and troubleshooting of more complicated logic around parsing command
    outputs.
    """

    def __init__(self, full_script_path):
        super(DirectScript, self).__init__(full_script_path)
        self.logger.debug("<INIT> Building Direct Session Object")

        valid_response = ["yes", "no"]
        response = ""
        while response.lower() not in valid_response:
            response = raw_input("Is this device already connected?({}): ".format(str(valid_response)))

        if response.lower() == "yes":
            self.logger.debug("<INIT> Assuming session is already connected")
            self._connected = True
        else:
            self.logger.debug("<INIT> Assuming session is NOT already connected")
            self._connected = False

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

    def is_connected(self):
        """
        Returns a boolean value that describes if the session is currently connected.

        :return: True if the session is connected, False if not.
        :rtype: bool
        """
        return self._connected

    def connect_ssh(self, host, username, password, version=None, prompt_endings=("#", ">")):
        """
        Connects to a device via the SSH protocol. By default, SSH2 will be tried first, but if it fails it will attempt
        to fall back to SSH1.

        :param host: The IP address of DNS name for the device to connect
        :type host: str
        :param username: The username to login to the device with
        :type username: str
        :param password: The password that goes with the provided username.  If a password is not specified, the
            user will be prompted for one.
        :type password: str
        :param version: The SSH version to connect with (1 or 2).  Default is None, which will try 2 first and fallback
            to 1 if that fails.
        :type version: int
        :param prompt_endings: A list of strings that are possible prompt endings to watch for.  The default is for
                               Cisco devices (">" and "#"), but may need to be changed if connecting to another
                               type of device (for example "$" for some linux hosts).
        :type prompt_endings: list
        """
        if version == 2 or version == 1:
            print "Pretending to log into device {} with username {} using SSH{}.".format(host, username, version)
        else:
            print "Pretending to log into device {} with username {} using SSH2.".format(host, username)
        self._connected = True

    def connect_telnet(self, host, username, password, prompt_endings=("#", ">")):
        """
        Connects to a device via the Telnet protocol.

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
        print "Pretending to log into device {} with username {} using TELNET.".format(host, username)
        self._connected = True

    def disconnect(self, command="exit"):
        """
        Disconnects the connected session by sending the "exit" command to the remote device.  If that does not make
        the disconnect happen, attempt to force and ungraceful disconnect.

        :param command: The command to be issued to the remote device to disconnect.  The default is 'exit'
        :type command: str
        """
        print "Pretending to disconnect from device {}.".format(self.hostname)
        self._connected = False

    def ssh_via_jump(self, host, username, password, options="-o StrictHostKeyChecking=no"):
        """
        From the connected session, this method issues the SSH command to connect to another box, using the main
        connected sessions as a jump point to reach the target.  In other words, connect_ssh() would be used to connect
        to the jump box/bastion host and then this method would be used to connect to the remote device via the jump
        host.

        If this method doesn't receive the expected prompts after issuing the credentials, an exception will be raised.

        :param host: IP address or hostname (resolvable on the jumpbox)
        :type host: str
        :param username: Username to log into the remote device with
        :type username: str
        :param password: Password for logging into the remote device
        :type password: str
        :param options: Additional "ssh" command paramters.  Default disables strict host key checking so that the
                        script will not be prompted to accept the remote key.
        :type options: str
        """
        if self.prompt:
            self.prompt_stack.insert(0,self.prompt)
        self.prompt = "{}#".format(host)
        print "Now connected to: {} (using prompt: {})".format(host, self.prompt)

    def telnet_via_jump(self, host, username, password):
        """
        From the connected session, this method issues the telnet command to connect to another box, using the main
        connected sessions as a jump point to reach the target.  In other words, connect_ssh() would be used to connect
        to the jump box/bastion host and then this method would be used to connect to the remote device via the jump
        host.

        If this method doesn't receive the expected prompts after issuing the credentials, an exception will be raised.

        :param host: IP address or hostname (resolvable on the jumpbox)
        :type host: str
        :param username: Username to log into the remote device with
        :type username: str
        :param password: Password for logging into the remote device
        :type password: str
        """
        if self.prompt:
            self.prompt_stack.insert(0,self.prompt)
        self.prompt = "{}#".format(host)
        print "Now connected to: {} (using prompt: {})".format(host, self.prompt)

    def disconnect_via_jump(self, command="exit"):
        """
        Issues a command to disconnect from the remote device, bringing us back to the jump host.  The default command
        is "exit", but it can be changed by passing in a different "command".  If we don't see the prompt for the jump
        host after issuing the disconnect command, an exception will be raised.

        :param command: The command to be issued to the remote device to disconnect.  The default is 'exit'
        :type command: str
        """
        prev_prompt = None
        try:
            prev_prompt = self.prompt_stack.pop(0)
            print "Simulated disconnect from remote host.  Now at prompt: {}".format(prev_prompt)
            self.prompt = prev_prompt
        except IndexError:
            print "Simulated disconnect from remote host.  Prompt not recorded from previous device".format
            self.prompt = prev_prompt

    def start_cisco_session(self, enable_pass=None):
        """
        Performs initial setup of the session to a Cisco device by detecting parameters (prompt, hostname, network OS,
        etc) of the connected device and modifying the terminal length if configured to do so in the settings file.

        If the device is not at an enable prompt and an enable password is supplied, then this method will also enter
        enable mode on the device before proceeding.

        This should always be called before trying to interact with a Cisco device so that the majority of other
        methods will work correctly.  This should be one of the first calls in a script that is intended to run when
        already connected to the device, or called right after connecting to a device with the "connect_ssh" or similar
        method.

        :param enable_pass: The enable password that should be sent if the device is not in enable mode.
        :type enable_pass: str
        """
        # Validate we are connected before trying to start a Cisco session
        if not self.is_connected():
            raise InteractionError("Session is not connected.  Cannot start Cisco session.")

        # Get prompt (and thus hostname) from device
        self.prompt = "DebugHost#"
        self.hostname = self.prompt[:-1]
        self.logger.debug("<START> Set Hostname: {}".format(self.hostname))

        # Detect the OS of the device, because outputs will differ per OS
        valid_os = ["IOS", "NXOS", "ASA"]
        response = ""
        while response not in valid_os:
            response = raw_input("Select OS ({0}): ".format(str(valid_os)))
        self.logger.debug("<INIT> Setting OS to {0}".format(response))
        self.os = response

        # Get terminal length and width, so we can revert back after changing them.
        self.term_len, self.term_width = None, None

        # If modify_term setting is True, then prevent "--More--" prompt (length) and wrapping of lines (width)
        if self.settings.getboolean("Global", "modify_term"):
            self.logger.debug("<START> Pretending to modify term setting.")

    def end_cisco_session(self):
        """
        End the session by returning the device's terminal parameters that were modified by start_session() to their
        previous values.

        This should always be called before a disconnect (assuming that start_cisco_session was called after connect)
        """
        self.logger.debug("<END> Ending Session")

        # Delete prompt and hostname attributes
        self.prompt = None
        self.logger.debug("<END> Deleting learned Prompt.")
        self.hostname = None
        self.logger.debug("<END> Deleting learned Hostname.")

        # Delete the detected OS
        self.os = None
        self.logger.debug("<END> Deleting Discovered OS.")

    def write_output_to_file(self, command, filename):
        """
        Send the supplied command to the remote device and writes the output to a file.

        This function was written specifically to write output line by line because storing large outputs into a
        variable will cause SecureCRT to bog down until it freezes.  A good example is a large "show tech" output.
        This method can handle any length of output

        :param command: The command to be sent to the device
        :type command: str
        :param filename: A string with the absolute path to the filename to be written.
        :type filename: str
        """
        input_filename = ""
        while not os.path.isfile(input_filename):
            input_filename = raw_input("Path to file with output from '{0}' ('q' to quit): ".format(command))
            if input_filename == 'q':
                exit(0)
            elif not os.path.isfile(input_filename):
                print "Invalid File, please try again..."

        with open(input_filename, 'r') as input_file:
            input_data = input_file.readlines()

        self.logger.debug("<WRITE OUTPUT> Call to write_output_to_file with command: {0}, filename: {1}"
                          .format(command, filename))
        self.validate_dir(os.path.dirname(filename))
        self.logger.debug("<WRITE OUTPUT> Using filename: {0}".format(filename))

        # Write the output to the specified file
        try:
            # Need the 'b' in mode 'wb', or else Windows systems add extra blank lines.
            with open(filename, 'wb') as newfile:
                for line in input_data:
                    newfile.write(line.strip('\r\n').encode('ascii', 'ignore') + "\r\n")
                    self.logger.debug("<WRITE OUTPUT> Writing Line: {0}".format(line.strip('\r\n')
                                                                                .encode('ascii', 'ignore')))
        except IOError, err:
            error_str = "IO Error for:\n{0}\n\n{1}".format(filename, err)
            self.message_box(error_str, "IO Error", ICON_STOP)

    def get_command_output(self, command):
        """
        Captures the output from the provided command and saves the results in a variable.

        ** NOTE ** Assigning the output directly to a variable causes problems with SecureCRT for long outputs.  It
        will gradually get slower and slower until the program freezes and crashes.  The workaround is to
        save the output directly to a file (line by line), and then read it back into a variable.  This is the
        procedure that this method uses.

        Keyword Arguments:
            :param command: Command string that should be sent to the device
            :type command: str

        :return: The result from issuing the above command.
        :rtype: str
        """
        self.logger.debug("<GET OUTPUT> Running get_command_output with input {0}".format(command))
        # Create a temporary filename
        temp_filename = self.create_output_filename("{0}-temp".format(command))
        self.logger.debug("<GET OUTPUT> Temp Filename".format(temp_filename))
        self.write_output_to_file(command, temp_filename)
        with open(temp_filename, 'r') as temp_file:
            result = temp_file.read()

        if self.settings.getboolean("Global", "debug_mode"):
            filename = os.path.split(temp_filename)[1]
            new_filename = os.path.join(self.debug_dir, filename)
            self.logger.debug("<GET OUTPUT> Moving temp file to {0}".format(new_filename))
            os.rename(temp_filename, new_filename)
        else:
            self.logger.debug("<GET OUTPUT> Deleting {0}".format(temp_filename))
            os.remove(temp_filename)
        self.logger.debug("<GET OUTPUT> Returning results of size {0}".format(sys.getsizeof(result)))
        return result

    def send_config_commands(self, command_list, output_filename=None):
        """
        This method accepts a list of strings, where each string is a command to be sent to the device.

        This method will send "conf t", then all the commands from the list and finally send "end" to the device.
        If an output_filenameThe results returned from entering the commands into the device are written to a file.

        NOTE: This method is new and does not have any error checking for how the remote device handles the commands
        you are trying to send.  USE IT AT YOUR OWN RISK.

        :param command_list: A list of strings, where each string is a command to be sent.  This should NOT include
                            'config t' or 'end'.  This is added automatically.
        :type command_list: list
        :param output_filename: (Optional) If a absolute path to a file is specified, the config session output from
                                applying the commands will be written to this file.
        :type output_filename: str
        """
        self.logger.debug("<SEND CONFIG> Preparing to write commands to device.")
        self.logger.debug("<SEND CONFIG> Received: {}".format(str(command_list)))

        command_string = ""
        command_string += "configure terminal\n"
        for command in command_list:
            command_string += "{}\n".format(command.strip())
        command_string += "end\n"

        self.logger.debug("<SEND CONFIG> Final command list:\n {}".format(command_string))

        output_filename = self.create_output_filename("CONFIG_RESULT")
        config_results = command_string
        with open(output_filename, 'w') as output_file:
            self.logger.debug("<SEND CONFIG> Writing output to: {}".format(output_filename))
            output_file.write("{}{}".format(self.prompt, config_results))

    def save(self, command="copy running-config startup-config"):
        """
        Sends a "copy running-config startup-config" command to the remote device to save the running configuration.
        """
        self.logger.debug("<SAVE> Simulating Saving configuration on remote device.")
        print "Saved config."

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
