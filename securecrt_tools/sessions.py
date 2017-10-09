# ################################################   MODULE INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# The module contains all the classes and functions necessary to represent a SecureCRT session (or simulate one)
#
#
#

# ################################################     IMPORTS      ###################################################
import os
import sys
import logging
import time
import datetime
import re
from abc import ABCMeta, abstractmethod


# #############################################  MESSAGEBOX CONSTANTS  ################################################
#
# These are used for MessageBox creation.
#
# Button parameter options.  These can be OR'd ( | ) together to combine one from each category, and the final value
# passed in as the option to the MessageBox.
#
# Options to display icons
ICON_STOP = 16                 # display the ERROR/STOP icon.
ICON_QUESTION = 32             # display the '?' icon
ICON_WARN = 48                 # display a '!' icon.
ICON_INFO= 64                  # displays "info" icon.
#
# Options to choose what types of buttons are available
BUTTON_OK = 0                  # OK button only
BUTTON_CANCEL = 1              # OK and Cancel buttons
BUTTON_ABORTRETRYIGNORE = 2    # Abort, Retry, and Ignore buttons
BUTTON_YESNOCANCEL = 3         # Yes, No, and Cancel buttons
BUTTON_YESNO = 4               # Yes and No buttons
BUTTON_RETRYCANCEL = 5         # Retry and Cancel buttons
#
# Options for which button is default
DEFBUTTON1 = 0        # First button is default
DEFBUTTON2 = 256      # Second button is default
DEFBUTTON3 = 512      # Third button is default
#
#
# Possible MessageBox() return values
IDOK = 1              # OK button clicked
IDCANCEL = 2          # Cancel button clicked
IDABORT = 3           # Abort button clicked
IDRETRY = 4           # Retry button clicked
IDIGNORE = 5          # Ignore button clicked
IDYES = 6             # Yes button clicked
IDNO = 7              # No button clicked


# ################################################     CLASSES      ###################################################

class Session:
    __metaclass__ = ABCMeta

    def __init__(self, script_path, settings_importer):
        self.script_dir, self.script_name = os.path.split(script_path)
        self.os = None
        self.prompt = None
        self.hostname = None
        self.logger = logging

        self.settings = settings_importer.get_settings_dict()

        if self.settings['debug']:
            save_path = os.path.realpath(self.settings['save path'])
            self.debug_dir = os.path.join(save_path, "debugs")
            log_file = os.path.join(self.debug_dir, self.script_name.replace(".py", "-debug.txt"))
            self.validate_path(log_file)
            self.logger = logging.getLogger("securecrt")
            self.logger.propagate = False
            self.logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S%pOK')
            fh = logging.FileHandler(log_file, mode='w')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            self.logger.debug("Starting Logging. Running Python version: {0}".format(sys.version))

    def validate_path(self, path):
        """
        Verify the directory to supplied file exists.  Create it if necessary (unless otherwise specified).

        :param path: The path to validate
        :return:
        """

        self.logger.debug("Starting validation of path: {0}".format(path))
        # Get the directory portion of the path
        base_dir = os.path.dirname(path)
        self.logger.debug("Base directory is {0}".format(base_dir))

        # Verify that base_path is valid absolute path, or else error and exit.
        if not os.path.isabs(base_dir):
            error_str = 'Directory is invalid. Please correct\n' \
                        'the path in the script settings.\n' \
                        'Dir: {0}'.format(base_dir)
            self.message_box(error_str, "Path Error", ICON_STOP)
            self.end()
            sys.exit()

        # Check if directory exists.  If not, prompt to create it.
        if not os.path.exists(os.path.normpath(base_dir)):
            message_str = "The path: '{0}' does not exist.  Do you want to create it?.".format(base_dir)
            result = self.message_box(message_str, "Create Directory?", ICON_QUESTION | BUTTON_YESNO | DEFBUTTON2)

            if result == IDYES:
                os.makedirs(base_dir)
            else:
                self.message_box("Output directory does not exist.  Exiting.",
                                      "Invalid Path", ICON_STOP)
                self.end()
                sys.exit()

    def create_output_filename(self, desc, ext=".txt", include_date=True):
        """
        Generates a filename based on information from the connected device

        :param desc:  <str> Customer description to put in filename.
        :param ext:  Default extension is ".txt", but other extension can be supplied.
        :param include_date"  A boolean to specify whether the date string shoudl be included in the filename.
        :return:
        """

        self.logger.debug("Starting creation of filename with desc: {0}, ext: {1}, include_date: {2}"
                          .format(desc, ext, include_date))
        self.logger.debug("Original Save Path: {0}".format(self.settings['save path']))
        save_path = os.path.realpath(self.settings['save path'])
        self.logger.debug("Real Save Path: {0}".format(save_path))


        # If environment vars were used, expand them
        save_path = os.path.expandvars(save_path)
        # If a relative path was specified in the settings file, expand it.
        save_path = os.path.expandvars(os.path.expanduser(save_path))
        self.logger.debug("Expanded Save Path: {0}".format(save_path))

        # Remove reserved filename characters from filename
        clean_desc = desc.replace("/", "-")
        clean_desc = clean_desc.replace(".", "-")
        clean_desc = clean_desc.replace(":", "-")
        clean_desc = clean_desc.replace("\\", "")
        clean_desc = clean_desc.replace("| ", "")
        # Just in case the trailing space from the above replacement was missing.
        clean_desc = clean_desc.replace("|", "")

        if include_date:
            # Get the current date in the format supplied in date_format
            now = datetime.datetime.now()
            my_date = now.strftime(self.settings['date format'])
            self.logger.debug("Created Date String: {0}".format(my_date))
            file_bits = [self.hostname, clean_desc, my_date]
        else:
            file_bits = [self.hostname, desc]

        self.logger.debug("Using {0} to create filename".format(file_bits))
        # Create Filename based on hostname and date format string.
        filename = '-'.join(file_bits)
        filename = filename + ext
        file_path = os.path.normpath(os.path.join(save_path, filename))
        self.logger.debug("Final Filename: {0}".format(file_path))

        return file_path

    @abstractmethod
    def end(self):
        pass

    @abstractmethod
    def message_box(self, message, title="", options=0):
        pass

    @abstractmethod
    def prompt_window(self, message, title="", hide_input=False):
        pass

    @abstractmethod
    def file_open_dialog(self, title, open_type, file_filter):
        pass

    @abstractmethod
    def get_command_output(self, command):
        pass

    @abstractmethod
    def write_output_to_file(self, command, filename):
        pass

    @abstractmethod
    def create_new_saved_session(self, session_name, ip, protocol="SSH2", folder="_imports"):
        pass

    @abstractmethod
    def send_config_commands(self, command_list):
        pass


class CRTSession(Session):

    def __init__(self, crt, settings_importer):
        self.crt = crt
        super(CRTSession, self).__init__(crt.ScriptFullName, settings_importer)
        self.logger.debug("Starting creation of CRTSession object")

        # Set up SecureCRT tab for interaction with the scripts
        self.tab = self.crt.GetScriptTab().Screen

        if self.crt.Session.Connected == 0:
            self.logger.debug("Session not connected prior to creating object.")
        else:
            self.logger.debug("Session already connected.  Setting up.")
            self.__start()

    def __start(self):
        # Set Tab parameters to allow correct sending/receiving of data via SecureCRT
        self.tab.Synchronous = True
        self.tab.IgnoreEscape = True
        self.logger.debug("Set Syncronous and IgnoreEscape")

        # Get prompt (and thus hostname) from device
        self.prompt = self.__get_prompt()
        self.logger.debug("Set Prompt: {0}".format(self.prompt))
        self.hostname = self.prompt[:-1]
        self.logger.debug("Set Hostname: {0}".format(self.hostname))

        # Detect the OS of the device, because outputs will differ per OS
        self.os = self.__get_network_os()
        self.logger.debug("Discovered OS: {0}".format(self.os))

        # Get terminal length and width, so we can revert back after changing them.
        self.term_len, self.term_width = self.__get_term_info()
        self.logger.debug("Discovered Term Len: {0}, Term Width: {1}".format(self.term_len, self.term_width))

        # If modify_term setting is True, then prevent "--More--" prompt (length) and wrapping of lines (width)
        if self.settings['modify term']:
            self.logger.debug("Modify Term setting is set.  Sending commands to adjust terminal")
            if self.os == "IOS" or self.os == "NXOS":
                # Send term length command and wait for prompt to return
                if self.term_len:
                    self.tab.Send('term length 0\n')
                    self.tab.WaitForString(self.prompt)
            elif self.os == "ASA":
                if self.term_len:
                    self.tab.Send('terminal pager 0\r\n')
                    self.tab.WaitForString(self.prompt)

            # Send term width command and wait for prompt to return (depending on platform)

            if self.os == "IOS":
                if self.term_len:
                    self.tab.Send('term width 0\n')
                    self.tab.WaitForString(self.prompt)
            elif self.os == "NXOS":
                if self.term_len:
                    self.tab.Send('term width 511\n')
                    self.tab.WaitForString(self.prompt)

        # Added due to Nexus echoing twice if system hangs and hasn't printed the prompt yet.
        # Seems like maybe the previous WaitFor prompt isn't always working correctly.  Something to look into.
        time.sleep(0.1)

    def __get_prompt(self):
        """
        Returns the prompt of the device logged into.
        """

        # Send two line feeds to the device so the device will re-display the prompt line
        self.tab.Send("\r\n\r\n")

        # Waits for first linefeed to be echoed back to us
        wait_result = self.tab.WaitForString("\n", 5)
        if wait_result == 1:
            # Capture the text until we receive the next line feed
            prompt = self.tab.ReadString("\n", 5)
            # Remove any trailing control characters from what we captured
            prompt = prompt.strip()

            # Check for non-enable mode (prompt ends with ">" instead of "#")
            if prompt[-1] == ">":
                self.message_box("Not in enable mode.  Enter enable and try again.", "Not in Enable Mode", ICON_STOP)
                self.end()
                sys.exit()
            # If our prompt shows in a config mode -- there is a ) before # -- e.g. Router(config)#
            if prompt[-2] == ")":
                self.message_box("In config mode.  Exit config mode and try again.", "In Config Mode", ICON_STOP)
                self.end()
                sys.exit()
            elif prompt[-1] != "#":
                self.message_box("Unable to capture prompt.  Stopping script.", "Prompt Error", ICON_STOP)
                self.end()
                sys.exit()
            else:
                return prompt
        else:
            # If WaitForString timed out, return None to signal failure
            return None

    def __get_network_os(self):
        """
        Discovers OS type so that scripts can use them when necessary (e.g. commands vary by version)
        """
        send_cmd = "show version | i Cisco"

        raw_version = self.__get_output(send_cmd)
        self.logger.debug("Version String: {0}".format(raw_version))

        if "IOS XE" in raw_version:
            version = "IOS"
        elif "Cisco IOS Software" in raw_version or "Cisco Internetwork Operating System" in raw_version:
            version = "IOS"
        elif "Cisco Nexus Operating System" in raw_version:
            version = "NXOS"
        elif "Adaptive Security Appliance" in raw_version:
            version = "ASA"
        else:
            version = "Unknown"

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
        *** NOTE *** This is private because it should only be used when it is guaranteeds that the output will be
        small (less than 1000 lines), or else SecureCRT can crash.

        :param command: Command string that should be sent to the device
        :return result: Variable holding the result of issuing the above command.
        """
        # Send command
        self.tab.Send(command + '\n')

        # Ignore the echo of the command we typed
        self.tab.WaitForString(command.strip())

        # Capture the output until we get our prompt back and write it to the file
        result = self.tab.ReadString(self.prompt)

        return result.strip('\r\n')

    def login(self, host, username, password=None):
        if not password:
            password = self.prompt_window("Enter the password for this device.", "Password", hide_input=True)

        login_string = "/SSH2 /ACCEPTHOSTKEYS /L {} /PASSWORD {} {}".format(username, password, host)
        if self.crt.Session.Connected == 0:
            connected = False
            try:
                self.logger.debug("Attempting Connection to: {}@{}".format(username, host))
                self.crt.Session.Connect(login_string)
                connected = True
            except:
                error = self.crt.GetLastErrorMessage()
                self.logger.debug("Error connecting: {}".format(error))
                self.message_box(error, "Connect Failed", ICON_STOP)

            if connected:
                self.__start()
        else:
            self.message_box("Session already connected.  Please disconnect before trying again.")

    def disconnect(self):
        self.logger.debug("Disconnecting Session")
        self.crt.Session.Disconnect()

    def end(self):
        """
                End the session by returning the device's terminal parameters back to normal.
                :return:
                """
        # If the 'tab' and 'prompt' options aren't in the session structure, then we aren't actually connected to a device
        #  when this is called, and there is nothing to do.
        self.logger.debug("Ending Session")
        if self.crt:
            if self.tab:
                if self.prompt:
                    if self.settings['modify term']:
                        self.logger.debug("Modify Term setting is set.  Sending commands to return terminal to normal.")
                        if self.os == "IOS" or self.os == "NXOS":
                            if self.term_len:
                                # Set term length back to saved values
                                self.tab.Send('term length {0}\n'.format(self.term_len))
                                self.tab.WaitForString(self.prompt)

                            if self.term_width:
                                # Set term width back to saved values
                                self.tab.Send('term width {0}\n'.format(self.term_width))
                                self.tab.WaitForString(self.prompt)
                        elif self.os == "ASA":
                            self.tab.Send("terminal pager {0}\n".format(self.term_len))

                self.tab.Synchronous = False
                self.tab.IgnoreEscape = False
                self.logger.debug("Unset Syncronous and IgnoreEscape")

    def message_box(self, message, title="", options=0):
        """
        Prints a message in a pop-up message box, and captures the response (which button clicked).  See the section
        at the top of this file "MessageBox Constants" to manipulate how the message box will look (which buttons are
        available

        :param message: <string> The message to print to the screen
        :param title: <string> Title for the message box
        :param options: <Integer> (See MessageBox Constansts at the top of this file)
        :return:
        """
        self.logger.debug("Creating MessageBox with Title: {0}, Message{1}, Options: {2}".format(title, message,
                                                                                                 options))
        return self.crt.Dialog.MessageBox(message, title, options)

    def prompt_window(self, message, title="", hide_input=False):
        self.logger.debug("Creating Prompt with message: '{0}'".format(message))
        result = self.crt.Dialog.Prompt(message, title, "", hide_input)
        self.logger.debug("Captures prompt results: '{0}'".format(result))
        return result

    def file_open_dialog(self, title, open_type, file_filter):
        result_filename = ""
        result_filename = self.crt.Dialog.FileOpenDialog(title, open_type, result_filename, file_filter)
        return result_filename

    def write_output_to_file(self, command, filename):
        """
        Send the supplied command to the session and writes the output to a file.

        This function was written specifically to write output line by line because storing large outputs into a variable
        will cause SecureCRT to bog down until it freezes.  A good example is a large "show tech" output.
        This method can handle any length of output

        :param command: The command to be sent to the device
        :param filename: The filename for saving the output
        """

        self.logger.debug("Call to write_output_to_file with command: {0}, filename: {1}".format(command, filename))
        self.validate_path(filename)
        self.logger.debug("Using filename: {0}".format(filename))

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

                self.tab.Send(command + "\n")

                # Ignore the echo of the command we typed (including linefeed)
                self.tab.WaitForString(command.strip())

                # Loop to capture every line of the command.  If we get CRLF (first entry in our "endings" list), then
                # write that line to the file.  If we get our prompt back (which won't have CRLF), break the loop b/c we
                # found the end of the output.
                while True:
                    nextline = self.tab.ReadString(matches)
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
                            self.logger.debug("Writing Line: {0}".format(nextline.strip('\r\n').encode('ascii',
                                                                                                       'ignore')))
                    elif self.tab.MatchIndex == 2:
                        # If we get a --More-- send a space character
                        self.tab.Send(" ")
                    elif self.tab.MatchIndex == 3:
                        # We got our prompt, so break the loop
                        break

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

        :param command: Command string that should be sent to the device
        :return result: Variable holding the result of issuing the above command.
        """
        self.logger.debug("Running get_command_output with input '{0}'".format(command))
        # Create a temporary filename
        temp_filename = self.create_output_filename("{0}-temp".format(command))
        self.logger.debug("Temp Filename".format(temp_filename))
        self.write_output_to_file(command, temp_filename)
        with open(temp_filename, 'r') as temp_file:
            result = temp_file.read()

        if self.settings['debug']:
            filename = os.path.split(temp_filename)[1]
            new_filename = os.path.join(self.debug_dir, filename)
            self.logger.debug("Moving temp file to {0}".format(new_filename))
            os.rename(temp_filename, new_filename)
        else:
            self.logger.debug("Deleting {0}".format(temp_filename))
            os.remove(temp_filename)
        self.logger.debug("Returning results of size {0}".format(sys.getsizeof(result)))
        return result

    def create_new_saved_session(self, session_name, ip, protocol="SSH2", folder="_imports"):
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
        self.logger.debug("Creating new session '{0}'".format(session_path))
        new_session.Save(session_path)

    def send_config_commands(self, command_list):
        """
        This method accepts a list of strings, where each string is a command to be sent to the device.  This method
        will send "conf t", plus all the commands and finally and "end" to the device and write the results to a file.

        NOTE: This method is new and does not have any error checking for how the remote device handles the commands
        you are trying to send.  USE IT AT YOUR OWN RISK.

        :param command_list: A list of strings, where each string is a command to be sent.  This should NOT include
                            'config t' or 'end'.  This is added automatically.
        :return:
        """
        self.logger.debug("Preparing to write commands to device.")
        self.logger.debug("Received: {}".format(str(command_list)))

        command_string = ""
        command_string += "configure terminal\n"
        for command in command_list:
            command_string += "{}\n".format(command.strip())
        command_string += "end\n"

        self.logger.debug("Final command list:\n {}".format(command_string))

        output_filename = self.create_output_filename("CONFIG_RESULT")
        self.tab.Send(command_string)
        config_results = self.tab.ReadString(self.prompt)
        with open(output_filename, 'w') as output_file:
            self.logger.debug("Writing output to: {}".format(output_filename))
            output_file.write("{}{}".format(self.prompt, config_results))


class DirectSession(Session):

    def __init__(self, full_script_path, settings_importer):
        super(DirectSession, self).__init__(full_script_path, settings_importer)
        self.logger.debug("Building Direct Session Object")
        self.prompt = "DebugHost#"
        self.hostname = "DebugHost"
        valid_os = ["IOS", "NXOS", "ASA"]

        response = ""
        while response not in valid_os:
            response = raw_input("Select OS ({0}): ".format(str(valid_os)))
        self.logger.debug("Setting OS to {0}".format(response))
        self.os = response

    def end(self):
        pass

    def message_box(self, message, title="", options=0):
        """
        Simulates the MessageBox from SecureCRT, but on the command line/cossole window.

        :param message: <string> The message to print to the screen
        :param title: <string> Title for the message box
        :param options: <Integer> (See MessageBox Constansts at the top of this file)
        :return:
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

        self.logger.debug("Creating Message Box, with Title: {0}, Message: {1}, and Options: {2}".format(title, message,
                                                                                                         options))
        # Extract the layout paramter in the options field
        layout = get_button_layout(options)
        self.logger.debug("Layout Value is: {0}".format(layout))

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
            self.logger.debug("Received: {0}".format(response))

        code = get_response_code(response)
        self.logger.debug("Returning Response Code: {0}".format(code))
        return code

    def prompt_window(self, message, title="", hide_input=False):
        self.logger.debug("Creating Prompt with message: '{0}'".format(message))
        result = raw_input("{0}: ".format(message))
        self.logger.debug("Captures prompt results: '{0}'".format(result))
        return result

    def file_open_dialog(self, title, open_type, file_filter):
        result_filename = raw_input("{0}, {1} (type {2}): ".format(open_type, title, file_filter))
        return result_filename

    def write_output_to_file(self, command, filename):
        """
        Imitates the write_output_to_file method from the CRTSession object for debgugging purposes.  It prompts for
        an imput file path to open and then write the output like happens with SecureCRT.

        :param command: <str> The command that gives the output we want to write to a file
        :param filename: <str> Output filename to write the output
        """
        input_file = ""
        while not os.path.isfile(input_file):
            input_file = raw_input("Path to file with output from '{0}' ('q' to quit): ".format(command))
            if input_file == 'q':
                exit(0)
            elif not os.path.isfile(input_file):
                print "Invalid File, please try again..."

        with open(input_file, 'r') as input:
            input_data = input.readlines()

        self.logger.debug("Call to write_output_to_file with command: {0}, filename: {1}".format(command, filename))
        self.validate_path(filename)
        self.logger.debug("Using filename: {0}".format(filename))

        # Write the output to the specified file
        try:
            # Need the 'b' in mode 'wb', or else Windows systems add extra blank lines.
            with open(filename, 'wb') as newfile:
                for line in input_data:
                    newfile.write(line.strip('\r\n').encode('ascii', 'ignore') + "\r\n")
                    self.logger.debug("Writing Line: {0}".format(line.strip('\r\n').encode('ascii', 'ignore')))
        except IOError, err:
            error_str = "IO Error for:\n{0}\n\n{1}".format(filename, err)
            self.message_box(error_str, "IO Error", ICON_STOP)

    def get_command_output(self, command):
        """
        Simulates captures the output from the provided command and saves the results in a variable, for debugging
        purposes.

        :param command: Command string that should be sent to the device
        :return result: Variable holding the result of issuing the above command.
        """
        self.logger.debug("Running get_command_output with input {0}".format(command))
        # Create a temporary filename
        temp_filename = self.create_output_filename("{0}-temp".format(command))
        self.logger.debug("Temp Filename".format(temp_filename))
        self.write_output_to_file(command, temp_filename)
        with open(temp_filename, 'r') as temp_file:
            result = temp_file.read()

        if self.settings['debug']:
            filename = os.path.split(temp_filename)[1]
            new_filename = os.path.join(self.debug_dir, filename)
            self.logger.debug("Moving temp file to {0}".format(new_filename))
            os.rename(temp_filename, new_filename)
        else:
            self.logger.debug("Deleting {0}".format(temp_filename))
            os.remove(temp_filename)
        self.logger.debug("Returning results of size {0}".format(sys.getsizeof(result)))
        return result

    def create_new_saved_session(self, session_name, ip, protocol="SSH2", folder="_imports"):
        now = datetime.datetime.now()
        creation_date = now.strftime("%A, %B %d %Y at %H:%M:%S")

        session_path = os.path.join(folder, session_name)
        desc = ["Created on {0} by script:".format(creation_date), os.path.join(self.script_dir, self.script_name)]
        print "Simulated saving session '{0}'\n  IP: {1}, protocol: {2}\n Description: {3}".format(session_path, ip,
                                                                                                  protocol, str(desc))

    def send_config_commands(self, command_list):
        self.logger.debug("Preparing to write commands to device.")
        self.logger.debug("Received: {}".format(str(command_list)))

        command_string = ""
        command_string += "configure terminal\n"
        for command in command_list:
            command_string += "{}\n".format(command.strip())
        command_string += "end\n"

        self.logger.debug("Final command list:\n {}".format(command_string))

        output_filename = self.create_output_filename("CONFIG_RESULT")
        config_results = command_string
        with open(output_filename, 'w') as output_file:
            self.logger.debug("Writing output to: {}".format(output_filename))
            output_file.write("{}{}".format(self.prompt, config_results))