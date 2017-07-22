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
import csv
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

global_defaults = {
            '__comment': "USE FORWARD SLASHES IN WINDOWS PATHS! "
                         "See https://github.com/PresidioCode/SecureCRT for settings details",
            '__version': "1.0",
            'debug-mode': False,
            'save_path': 'SecureCRT/ScriptOutput',
            'date format': '%Y-%m-%d-%H-%M-%S',
            'modify term': True
        }
global_settings_name = 'global_settings.json'


# ################################  FUNCTIONS   #################################


def load_settings(crt, script_dir, filename, defaults):
    """
    Loads the specified settings file.  Defaults to "global_settings.json".  If the settings file doesn't exist, create 
    it with default settings.
    
    :param crt: The provided SecureCRT object that controls the interaction with a SecureCRT window.
    :param script_dir: Directory where the script is being executed from
    :param filename: The settings filename to look for.
    :param defaults: The defaults settings to be compared against, or written if no settings exist.
    :return: settings: A dictionary with the settings found in "script_settings.json" 
    """

    settings_full_path = os.path.join(script_dir, filename)

    # If the settings file exists, read file and return settings.
    if os.path.isfile(settings_full_path):
        with open(settings_full_path, 'r') as json_file:
            try:
                settings = json.load(json_file)
            except ValueError as err:
                error_str = "Settings import error.\n\nFor Windows paths you must either use forward-slashes " \
                            "(C:/Output) or double-backslashes (C:\\\\Output).\n\n Orignial Error: {0}".format(err)
                crt.Dialog.MessageBox(error_str, "Settings Error", ICON_STOP)
                settings = None
                exit(0)

        # Validate settings contains everything it should, or fix it.
        if not valid_settings(settings, defaults):
            message_str = "The current global settings file is invalid.\n\nOverwriting file with new settings."
            crt.Dialog.MessageBox(message_str, "Settings Error", ICON_STOP)
            return None
        else:
            # If settings are valid, add script_dir and validate path
            settings['script_dir'] = script_dir

        # If the imported settings version is old, write the new version, copying original settings on top.
        if "__version" not in settings.keys() or settings["__version"] != defaults["__version"]:
            crt.Dialog.MessageBox("{0} was out of date and will be automatically updated to the latest version."
                                  .format(filename))
            settings = generate_settings(defaults, existing=settings)
            write_settings(crt, script_dir, filename, settings)
            settings["script_dir"] = script_dir
        return settings
    else:
        # If file doesn't exist, return None
        return None


def generate_settings(default_settings, existing=None):
    """
    A function to generate a settings JSON file, based on the provided defaults.  If existing settings are passed in,
    those will be written on top of the new defaults.  In the end, only the new fields should be added to the existing
    settings.
    
    :param default_settings: The default settings used as the base of the JSON file. 
    :param existing: (Optional) Existing settings that need to be preserved in the new settings.
    :return: A new settings dictionary
    """
    new_settings = dict(default_settings)

    if existing:
        for key in default_settings:
            if key in existing:
                new_settings[key] = existing[key]

    return new_settings


def write_settings(crt, script_dir, filename, settings):
    settings_full_path = os.path.join(script_dir, filename)

    with open(settings_full_path, 'w') as json_file:
        json.dump(settings, json_file, sort_keys=True, indent=4, separators=(',', ': '))


def valid_settings(imported, master):
    """
    Checks the imported settings to make sure all required items are included.

    :param imported:
    :param master:
    :return:
    """
    for setting in master.keys():
        if setting not in imported.keys():
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
    tab.Send("\r\n\r\n")

    # Waits for first linefeed to be echoed back to us
    wait_result = tab.WaitForString("\n",5)
    if wait_result == 1:
        # Capture the text until we receive the next line feed
        prompt = tab.ReadString("\n", 5)
        # Remove any trailing control characters from what we captured
        prompt = prompt.strip()
        # If our ReadString timed out (received empty string) return None, otherwise return what we received.
        if prompt == "":
            return None
        else:
            return prompt
    else:
        # If WaitForString timed out, return None to signal failure
        return None


def get_term_info(session):
    """
    A function that returns the current terminal length and width

    :param session:  Session data structure from start_session().
    :return: A 2-tuple containing the terminal length and the terminal width
    """
    re_num_exp = r'\d+'
    re_num = re.compile(re_num_exp)

    if session['OS'] == "IOS" or session['OS'] == "NX-OS":
        result = get_output(session, "show terminal | i Length")
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
    elif session['OS'] == "ASA":
        pager = get_output(session, "show pager")
        re_length = re_num.search(pager)
        if re_length:
            length = re_length.group(0)
        else:
            length = None

        term_info = get_output(session, "show terminal")
        re_width = re_num.search(term_info[1])
        if re_width:
            width = re_width.group(0)
        else:
            width = None

        return length, width
    else:
        return None, None


def get_network_os(session):
    """
    Discovers OS type so that scripts can use them when necessary (e.g. commands vary by version)

    :param session: Session data structure from start_session().
    """
    SendCmd = "show version | i Cisco"

    raw_version = get_output(session, SendCmd)

    if "IOS XE" in raw_version:
        version = "IOS"
    elif "Cisco IOS Software" in raw_version or "Cisco Internetwork Operating System" in raw_version:
        version = "IOS"
    elif "Cisco Nexus Operating System" in raw_version:
        version = "NX-OS"
    elif "Adaptive Security Appliance" in raw_version:
        version = "ASA"
    else:
        version = "Unknown"
    return version


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
    settings = load_settings(crt, script_dir, global_settings_name, global_defaults)

    # If settings file exists
    if not settings:
        new_settings = generate_settings(global_defaults)
        write_settings(crt, script_dir, global_settings_name, new_settings)
        setting_msg = ("Personal settings file, {0}, created in directory:\n'{1}'\n\n"
                       "Please edit this file to make any settings changes.\n\n"
                       "After editing the settings, please run the script again."
                       ).format(global_settings_name, script_dir)
        crt.Dialog.MessageBox(setting_msg, "Settings Created", ICON_INFO)
        return None

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

        # Detect and store the OS of the attached device
        session['OS'] = get_network_os(session)

        session['term length'], session['term width'] = get_term_info(session)

        # If modify_term setting is True, then prevent "--More--" prompt (length) and wrapping of lines (width)
        if settings['modify term']:
            if session['OS'] == "IOS" or session['OS'] == "NX-OS":
                # Send term length command and wait for prompt to return
                if session['term length']:
                    tab.Send('term length 0\n')
                    tab.WaitForString(prompt)
            elif session['OS'] == "ASA":
                if session['term length']:
                    tab.Send('terminal pager 0\r\n')
                    tab.WaitForString(prompt)

            # Send term width command and wait for prompt to return (depending on platform)

            if session['OS'] == "IOS":
                if session['term width']:
                    tab.Send('term width 0\n')
                    tab.WaitForString(prompt)
            elif session['OS'] == "NX-OS":
                if session['term length']:
                    tab.Send('term width 511\n')
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

        settings = session['settings']
        if settings['modify term']:
            if session['OS'] == "IOS" or session['OS'] == "NX-OS":
                if session['term length']:
                    # Set term length back to saved values
                    tab.Send('term length {0}\n'.format(session['term length']))
                    tab.WaitForString(prompt)

                if session['term width']:
                    # Set term width back to saved values
                    tab.Send('term width {0}\n'.format(session['term width']))
                    tab.WaitForString(prompt)
            elif session['OS'] == "ASA":
                tab.Send("terminal pager {0}\n".format(session['term length']))

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
    settings = session['settings']
    save_path = settings['save_path']
    # If environment vars were used, expand them
    save_path = os.path.expandvars(save_path)
    # If a relative path was specified in the settings file, expand it.
    save_path = expanded_path(save_path)

    # Remove reserved filename characters from filename
    clean_desc = desc.replace("/", "-")
    clean_desc = clean_desc.replace(".", "-")
    clean_desc = clean_desc.replace(":", "-")
    clean_desc = clean_desc.replace("\\", "")
    clean_desc = clean_desc.replace("| ", "")
    # Just in case the trailing space from the above replacement was missing.
    clean_desc = clean_desc.replace("|", "")

    # Extract hostname from the session information
    hostname = session['hostname']

    if include_date:
        date_format = settings['date format']
        # Get the current date in the format supplied in date_format
        mydate = get_date_string(date_format)
        file_bits = [hostname, clean_desc, mydate]
    else:
        file_bits = [hostname, desc]

    # Create Filename based on hostname and date format string.
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
                crt.Dialog.MessageBox("Output directory does not exist.  Exiting.",
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
    if session['OS'] == "IOS" or session['OS'] == "NX-OS":
        matches = ["\r\n", '--More--', prompt]
    elif session['OS'] == "ASA":
        matches = ["\r\n", '<--- More --->', prompt]
    else:
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


def list_of_lists_to_csv(session, data, filename):
    """
    Takes a list of lists and writes it to a csv file.

    This function takes a list of lists, such as:

    [ ["IP", "Desc"], ["1.1.1.1", "Vlan 1"], ["2.2.2.2", "Vlan 2"] ]

    and writes it into a CSV file with the filename supplied.   Each sub-list
    in the outer list will be written as a row.  If you want a header row, it 
    must be the first sub-list in the outer list.

    :param data:  A list of lists data structure (one row per line of the CSV)
    :param filename:  The output filename for the CSV file
    """
    # Validate path before creating file.
    validate_path(session, filename)

    # Binary mode required ('wb') to prevent Windows from adding linefeeds after each line.
    newfile = open(filename, 'wb')
    csv_out = csv.writer(newfile)
    for line in data:
        csv_out.writerow(line)
    newfile.close()


def list_of_dicts_to_csv(session, fields, data, filename):
    """
    Accepts a list of dictionaries and writes it to a CSV file.

    This function takes a list of dicts (passed in as data), such as:

    [ {"key1": value, "key2": value}, {"key1": value, "key2": value} ]

    and puts it into a CSV file with the supplied filename.  The function requires 
    a list of the keys found in the dictionaries (passed in as fields), such as:

    [ "key1", "key2" ]

    This will write a CSV file with all of the keys as the header row, and add a
    row for every dict in the list, with the correct data in each column.

    :param fields:  The list of header fields
    :param data:   The list of dictionaries, where each key in the dict corresponds to a header value
    :param filename:  The output filename to write
    """
    # Validate path before creating file.
    validate_path(session, filename)

    with open(filename, "wb") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writerow(dict(zip(writer.fieldnames, writer.fieldnames)))
        for entry in data:
            writer.writerow(entry)


def create_session(session, session_name, ip, protocol="SSH2", folder="_imports"):
    crt = session['crt']
    creation_date = get_date_string("%A, %B %d %Y at %H:%M:%S")

    # Create a session from the configured default values.
    new_session = crt.OpenSessionConfiguration("Default")

    # Set options based)
    new_session = crt.OpenSessionConfiguration("Default")
    new_session.SetOption("Protocol Name", protocol)
    new_session.SetOption("Hostname", ip)
    desc = ["Created on {} by script:".format(creation_date), crt.ScriptFullName]
    new_session.SetOption("Description", desc)
    session_path = os.path.join(folder, session_name)
    # Save session based on passed folder and session name.
    new_session.Save(session_path)


# ######################  DISPLAY ERROR IF RAN DIRECTLY  #######################


def main():
    error_str = "This is not a SecureCRT Script,\n" \
                "But a python module that holds\n" \
                "functions for other scripts to use.\n\n"

    crt.Dialog.MessageBox(error_str, "NOT A SCRIPT", ICON_STOP)

if __name__ == "__builtin__":
    main()
