# ###############################  MODULE  INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
#    !!!! NOTE:  THIS IS NOT A SCRIPT THAT CAN BE RUN IN SECURECRT. !!!!
#
# This is a Python module that contains commonly used functions for interacting with SecureCRT.  These functions assume
# that the session is connected to a Cisco device.  These functions can be imported into the scripts that will be run
# directly from SecureCRT, to abstract away some of the more complex aspects of interacting with the session.
#
#

# #################################  IMPORTS   ##################################
import os
import sys
import time
import json
import re
from py_utils import get_date_string
from py_utils import expanded_path


# ###########################  MESSAGEBOX CONSTANTS  ############################
#
# These are used for MessageBox creation.
#
# Button parameter options.  These can be OR'd ( | ) together to combine one
# from each category.
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


# ################################   DEFAULTS    #################################

# Default settings that should be in the settings file.

default_settings = {
            '__comment': "USE FORWARD SLASHES IN WINDOWS PATHS! "
                         "See https://gitlab.presidio.com/jcaesar/securecrt-scripts for settings details",
            'debug-mode': False,
            'save path': 'SecureCRT/ScriptOutput',
            'date format': '%Y-%m-%d-%H-%M-%S',
            'modify term': True
        }
settings_filename = 'script_settings.json'


# ################################  FUNCTIONS   #################################


def load_settings(crt, script_dir):
    """
    Loads settings from "script_settings.json" if it exists.  Otherwise create it with default settings.

    :param crt: The provided SecureCRT object that controls the interaction with a SecureCRT window.
    :param script_dir: Directory where the script is being executed from
    :return settings: A dictionary with the settings found in "script_settings.json"
    """
    # TODO Update to handle backslashes in path (escape backslash on write?)
    settings_full_path = os.path.join(script_dir, settings_filename)
    if os.path.isfile(settings_full_path):
        with open(settings_full_path, 'r') as json_file:
            settings = json.load(json_file)
        return settings
    else:
        settings = generate_settings()
        write_settings(crt, script_dir, settings)
        return settings


def generate_settings(existing=None):
    new_settings = dict(default_settings)

    if existing:
        for key in default_settings:
            if key in existing:
                new_settings[key] = existing[key]

    return new_settings


def write_settings(crt, script_dir, settings):
    settings_full_path = os.path.join(script_dir, settings_filename)

    with open(settings_full_path, 'w') as json_file:
        json.dump(settings, json_file, sort_keys=True, indent=4, separators=(',', ': '))

    setting_msg = ("Personal settings file, {}, created in directory:\n'{}'\n\n"
                   "Please edit this file to make any settings changes."
                   ).format(settings_filename, script_dir)
    crt.Dialog.MessageBox(setting_msg, "Settings Created", ICON_INFO)


def valid_settings(imported):
    """
    Checks the imported settings to make sure all required items are included.

    :param imported:
    :return:
    """
    for setting in default_settings:
        if setting not in imported:
            return False
    return True


def get_prompt(tab):
    """
    Returns the prompt of the device logged into.

    Arguments:
        tab -- crt.GetScriptTab().screen object, which is used to interact with the appropriate tab in the main window.

    Returns:
        A string object containing the prompt captures from the device session.
    """

    # Send two line feeds to the device
    tab.Send("\n\n")

    # Waits for first linefeed to be echoed back to us
    tab.WaitForString("\n")

    # Capture the text until we receive the next line feed
    prompt = tab.ReadString("\n")

    # Remove any trailing control characters from what we captured
    prompt = prompt.strip()

    return prompt


def get_term_info(session):
    """
    A function that returns the current terminal length and width

    :param session:  Session data structure from start_session().
    :return: A 2-tuple containing the terminal length and the terminal width
    """

    re_num_exp = r'\d+'
    re_num = re.compile(re_num_exp)

    result = get_output(session, "show terminal | i Length")
    dim = result.split(',')

    return re_num.search(dim[0]).group(0), re_num.search(dim[1]).group(0)


def get_network_os(session):
    """
    Discovers OS type so that scripts can use them when necessary (e.g. commands vary by version)

    :param session: Session data structure from start_session().
    """

    SendCmd = "show version | i Cisco"

    version = get_output(session, SendCmd)
    ver_lines = version.split("\n")

    if "IOS XE" in ver_lines[0]:
        return "IOS XE"
    elif "Cisco IOS Software" in ver_lines[0] or \
         "Cisco Internetwork Operating System" in ver_lines[0]:
        return "IOS"
    elif "Cisco Nexus Operating System" in ver_lines[0]:
        return "NX-OS"
    else:
        return "Unknown"


def start_session(crt, script_dir):
    """
    Performs session setup and returns information needed for scripts to operate

    This function performs all the usual session setup commands and returns
    a dictionary containing necessary information for scripts to interact
    with the SecureCRT session.


    :param crt:  The provided SecureCRT object that controls the interaction with a SecureCRT window.
    :param script_dir:  The directory where the calling script is located.
    :return:  A dictionary that contains various session information, including:
                - The crt and tab objects used to interact with a SecureCRT window.
                - Settings from the "script_settings.json" file
                - The prompt and hostname of the connected device
                - The cisco terminal length and width
    """

    # Create data structure to store our session data.  Additional info added later.
    session = {}

    # Import Settings from Settings File or Default settings
    settings = load_settings(crt, script_dir)

    if not valid_settings(settings):
        message_str = "The current script_settings file is incomplete.\n\nWould you to attempt an automatic fix?"
        result = crt.Dialog.MessageBox(message_str, "Rebuild Settings?", ICON_QUESTION |
                                       BUTTON_CANCEL | DEFBUTTON2)

        if result == IDOK:
            new_settings = generate_settings(existing=settings)
            write_settings(crt, script_dir, new_settings)
            settings = load_settings(crt, script_dir)
        else:
            err_msg = ('The current script_settings file is incomplete.\n'
                       'Delete your {} and run the script again to generate a new settings file from defaults.\n\n'
                       )
            crt.Dialog.MessageBox(str(err_msg), "Settings Error", ICON_STOP)
            exit(0)

    session['settings'] = settings

    # Create a "Tab" object, so that all the output goes into the correct Tab.
    objTab = crt.GetScriptTab()

    # Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"
    tab = objTab.Screen

    session['crt'] = crt
    session['tab'] = tab

    # Set Tab parameters to allow correct sending/receiving of data via SecureCRT
    tab.Synchronous = True
    tab.IgnoreEscape = True

    # Get the prompt of the device
    prompt = get_prompt(tab)
    # Check for non-enable mode (prompt ends with ">" instead of "#")
    if prompt[-1] == ">":
        crt.Dialog.MessageBox("Not in enable mode.  Enter enable and try again.",
            "Not in Enable Mode", ICON_STOP)
        end_session(session)
        sys.exit()
    # If our prompt shows in a config mode -- there is a ) before # -- e.g. Router(config)#
    if prompt[-2] == ")":
        crt.Dialog.MessageBox("In config mode.  Exit config mode and try again.",
                              "In Config Mode", ICON_STOP)
        sys.exit()
    elif prompt[-1] != "#":
        crt.Dialog.MessageBox("Unable to capture prompt.  Stopping script.",
            "Prompt Error", ICON_STOP)
        sys.exit()
    else:
        session['prompt'] = prompt
        session['hostname'] = prompt[:-1]

        session['term length'], session['term width'] = get_term_info(session)

        # Detect and store the OS of the attached device
        session['OS'] = get_network_os(session)

        # If modify_term setting is True, then prevent "--More--" prompt (length) and wrapping of lines (width)
        if settings['modify term']:
            # Send term length command and wait for prompt to return
            tab.Send('term length 0\n')
            tab.WaitForString(prompt)

            # Send term width command and wait for prompt to return
            if session['OS'] == "NX-OS":
                tab.Send('term width 511\n')
            else:
                tab.Send('term width 0\n')
            tab.WaitForString(prompt)

        # Added due to Nexus echoing twice if system hangs and hasn't printed the prompt yet.
        # Seems like maybe the previous WaitFor prompt isn't always working correctly.  Something to look into.
        time.sleep(0.1)

    return session


def end_session(session):
    """
    Terminates the session by returning terminal options to their pre-script values

    :param session:  Session data from start_session()
    """
    # If the 'tab' and 'prompt' options aren't in the session structure, then we aren't actually connected to a device
    #  when this is called, and there is nothing to do.
    if session['tab'] and session['prompt']:
        tab = session['tab']
        prompt = session['prompt']

        len_str = 'term length {0}\n'.format(session['term length'])
        width_str = 'term width {0}\n'.format(session['term width'])

        settings = session['settings']
        if settings['modify term']:
            # Set term length back to saved values
            tab.Send(len_str)
            tab.WaitForString(prompt)

            # Set term width back to saved values
            tab.Send(width_str)
            tab.WaitForString(prompt)

        tab.Synchronous = False
        tab.IgnoreEscape = False


def get_output(session, command):
    """
    A function that issues a command to the current session and returns the output as a string variable

    :param session: Session data from start_session()
    :param command: Command string that should be sent to the device
    :return result: Variable holding the result of issuing the above command.
    """
    # Extract tab and prompt data
    prompt = session['prompt']
    tab = session['tab']

    # Send command
    tab.Send(command + '\n')

    # Ignore the echo of the command we typed
    tab.WaitForString(command.strip())

    # Capture the output until we get our prompt back and write it to the file
    result = tab.ReadString(prompt)

    return result.strip('\r\n')


def create_output_filename(session, desc, ext=".txt", include_date=True):
    """
    Generates a filename based on information from the user settings and a supplied description

    :param session:  Session data from start_session()
    :param desc:  Started
    :param ext:  Default extension is ".txt", but other extension can be supplied.
    :param include_date"  A boolean to specify whether the date string shoudl be included in the filename.
    :return:
    """
    # Extract path and format information from our tuple
    crt = session['crt']
    settings = session['settings']
    save_path = settings['save path']
    if include_date:
        date_format = settings['date format']
        # Get the current date in the format supplied in date_format
        mydate = get_date_string(date_format)
    else:
        mydate = ""

    # If environment vars were used, expand them
    save_path = os.path.expandvars(save_path)
    # If a relative path was specified in the settings file, expand it.
    save_path = expanded_path(save_path)

    # Extract hostname from the session information
    hostname = session['hostname']

    # Create Filename based on hostname and date format string.
    file_bits = [hostname, desc, mydate]
    filename = '-'.join(file_bits)
    filename = filename + ext
    file_path = os.path.normpath(os.path.join(save_path, filename))

    return file_path


def validate_path(session, path, create_on_notexist=True):
    """
    Verify the directory to supplied file exists.  Create it if necessary (unless otherwise specified).

    :param session:  Session data from start_session()
    :param path:  Full path to file
    :param create_on_notexist:  If True, SecureCRT will prompt to create the directory if it does not exist.
    """
    crt = session['crt']

    # Get the directory portion of the path
    base_dir = os.path.dirname(path)

    # Verify that base_path is valid absolute path, or else error and exit.
    if not os.path.isabs(base_dir):
        error_str = 'Directory is invalid. Please correct\n' \
                    'the path in the script settings.\n' \
                    'Dir: {0}'.format(base_dir)
        crt.Dialog.MessageBox(error_str, "Path Error", ICON_STOP)
        end_session(session)
        sys.exit()

    # Check if directory exists.  If not, prompt to create it.
    if not os.path.exists(os.path.normpath(base_dir)):
        if create_on_notexist:
            message_str = "The path: '{0}' does not exist.  Press OK to " \
                          "create, or cancel.".format(base_dir)
            result = crt.Dialog.MessageBox(message_str, "Create Directory?", ICON_QUESTION |
                                           BUTTON_CANCEL | DEFBUTTON2)

            if result == IDOK:
                os.makedirs(base_dir)
            else:
                crt.Dialog.MessageBox("Save path does not exist.  Exiting.",
                                      "Invalid Path", ICON_STOP)
                end_session(session)
                sys.exit()
        else:
            message_str = "The path: '{0}' does not exist.  Exiting.".format(base_dir)
            crt.Dialog.MessageBox(message_str, "Invalid Path", ICON_STOP)
            end_session(session)
            sys.exit()


def write_output_to_file(session, command, filename):
    """
    Send the supplied command to the session and writes the output to a file.

    This function was written specifically to write output line by line because storing large outputs into a variable
    will cause SecureCRT to bog down until it freezes.  A good example is a large "show tech" output.
    This method can handle any length of output

    :param session: Session data from start_session()
    :param command: The command to be sent to the device
    :param filename: The filename for saving the output
    """

    prompt = session['prompt']
    tab = session['tab']

    validate_path(session, filename)

    # RegEx to match the whitespace and backspace commands after --More-- prompt
    exp_more = r' [\b]+[ ]+[\b]+(?P<line>.*)'
    re_more = re.compile(exp_more)

    # The 3 different types of lines we want to match (MatchIndex) and treat differntly
    matches = ["\r\n", '--More--', prompt]

    # Write the output to the specified file
    try:
        # Need the 'b' in mode 'wb', or else Windows systems add extra blank lines.
        with open(filename, 'wb') as newfile:
            # Send command
            tab.Send(command + "\n")

            # Ignore the echo of the command we typed (including linefeed)
            tab.WaitForString(command.strip())

            # Loop to capture every line of the command.  If we get CRLF (first entry in our "endings" list), then
            # write that line to the file.  If we get our prompt back (which won't have CRLF), break the loop b/c we
            # found the end of the output.
            while True:
                nextline = tab.ReadString(matches)
                # If the match was the 1st index in the endings list -> \r\n
                if tab.MatchIndex == 1:
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
                elif tab.MatchIndex == 2:
                    # If we get a --More-- send a space character
                    tab.Send(" ")
                elif tab.MatchIndex == 3:
                    # We got our prompt, so break the loop
                    break

    except IOError, err:
        crt = session['crt']
        error_str = "IO Error for:\n{0}\n\n{1}".format(filename, err)
        crt.Dialog.MessageBox(error_str, "IO Error", ICON_STOP)


# ######################  DISPLAY ERROR IF RAN DIRECTLY  #######################


def main():
    error_str = "This is not a SecureCRT Script,\n" \
                "But a python module that holds\n" \
                "functions for other scripts to use.\n\n"

    crt.Dialog.MessageBox(error_str, "NOT A SCRIPT", ICON_STOP)

if __name__ == "__builtin__":
    main()
