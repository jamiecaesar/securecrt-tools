# $language = "python"
# $interface = "1.0"

import os
import sys
import logging
from ConfigParser import NoOptionError

# Add script directory to the PYTHONPATH so we can import our modules (only if run from SecureCRT)
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))

# Now we can import our custom modules
from securecrt_tools import scripts
from securecrt_tools import utilities
from securecrt_tools.message_box_const import ICON_QUESTION, BUTTON_YESNO, IDYES, IDNO

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def document(session, command_list_name, folder_per_device, prompt_create_dirs=True):
    """
    This function captures the output of the provided commands and writes them to files.  This is separated into a
    separate function so it can be called by both the single-device and multi-device version of this script.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
            SecureCRTSession or DirectSession)
    :type session: sessions.Session
    :param command_list: A list of commands that will be sent to the connected device.  Each output will be saved to a
            different file.
    :type command_list: list
    :param output_dir: The full path to the directory where the output files are written.
    :type output_dir: str
    :param folder_per_device: A boolean that if true will create a separate folder for each device
    :type folder_per_device: bool
    :return:
    """
    script = session.script

    # Get command list for this device.  This is done here instead of the main script so this function can be used by
    # the multi-device version of this script.
    if command_list_name:
        try:
            command_list = script.settings.getlist("document_device", command_list_name)
        except NoOptionError:
            script.message_box("The list {0} was not found in [document_device] section of the settings.ini file."
                               .format(command_list_name))
            return
    else:
        try:
            # Not using custom lists, so just get the list for the OS
            command_list = script.settings.getlist("document_device", session.os)
        except NoOptionError:
            script.message_box("The list {0} was not found in [document_device] section of the settings.ini file."
                               .format(session.os))
            return

    if folder_per_device:
        output_dir = os.path.join(script.output_dir, utilities.path_safe_name(session.hostname))
    else:
        output_dir = script.output_dir

    # Loop through each command and write the contents to a file.
    for command in command_list:
        # Generate filename used for output files.
        full_file_name = session.create_output_filename(command, include_hostname=not folder_per_device,
                                                        base_dir=output_dir)
        # Get the output of our command and save it to the filename specified
        session.write_output_to_file(command, full_file_name, prompt_to_create=prompt_create_dirs)

        # If we captured nothing, or an error then delete the file
        utilities.remove_empty_or_invalid_file(full_file_name)


def script_main(session):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will grab the output for a list of commands from the connected device.  The list of commands is taken
    from the 'settings/settings.ini' file.  There is a separate list for each supported network operating system (IOS,
    NXOS and ASA) and by default the list that matches the network operating system of the connected device will be
    used.

    Custom lists of commands are supported.  These lists can be added manually to the [document_device] section of the
    'settings/settings.ini' file.  To be able to choose one of these lists when running the script, the
    'prompt_for_custom_lists' setting needs to be changed to 'True' in the settings.ini file.  Once this option is
    enabled, the script will prompt for the name of the list that you want to use.  If the input is left blank then
    the default behavior (based on network OS) will choose the list.

    **Script Settings** (found in settings/settings.ini):

    * | **show_instructions** - When True, displays a pop-up upon launching the script
      | explaining where to modify the list of commands sent to devices.  This window also
      | prompts the user if they want to continue seeing this message.  If not, the script
      | changes this setting to False.
    * | **folder_per_device** - If True, Creates a folder for each device, based on the
      | hostname, and saves all files inside that folder WITHOUT the hostname in the output
      | file names.  If False, it saves all the files directly into the output folder from
      | the global settings and includes the hostname in each individual filename.
    * | **prompt_for_custom_lists** - When set to True, the script will prompt the user to
      | type the name of a list of commands to use with the connected device.  This list
      | name must be found as an option in the [document_device] section of the
      | settings.ini file.  The format is the same as the default network OS lists, 'ios',
      | 'nxos', etc.
    * | **ios** - The list of commands that will be run on IOS devices
    * | **nxos** - The list of commands that will be run on NXOS devices
    * | **asa** - The list of commands that will be run on ASA devices

    **Any additional options found in this section would be custom added by the user and are expected to be lists of
    commands for use with the 'prompt_for_custom_lists' setting.**

    By default, The outputs will be saved in a folder named after the hostname of the device, with each output file
    being saved inside that directory.  This behavior can be changed in the settings above.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["IOS", "NXOS", "ASA", "IOS-XR"])

    # Display instructions message, unless settings prevent it
    show_instructions = script.settings.getboolean("document_device", "show_instructions")
    if show_instructions:
        response = script.message_box("The list of commands sent to the device can be edited in the 'settings/settings."
                                      "ini' file in the main securecrt-tools directory.\nSee the documentation for this"
                                      " script for more details.\n\nDo you want to stop seeing this message?",
                                      "Instructions", ICON_QUESTION + BUTTON_YESNO)
        if response == IDYES:
            script.settings.update("document_device", "show_instructions", False)

    # Check if settings allow for custom lists, and if so prompt for the list to use -- if not, just use the list for
    # the OS of the device connected
    custom_allowed = script.settings.getboolean("document_device", "prompt_for_custom_lists")
    if custom_allowed:
        command_list_name = script.prompt_window("Enter the name of the command list you want to use.\n\nThese lists are found "
                                         "in the [document_device] section of your settings.ini file\n",
                                         "Enter command list")
    else:
        command_list_name = None

    folder_per_device = script.settings.getboolean("document_device", "folder_per_device")

    # Document scripts according to settings captured above.  If we want folder_per_device, don't include hostname in
    # the filename and vice versa.
    document(session, command_list_name, folder_per_device)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Get session object for the SecureCRT tab that the script was launched from.
    crt_session = crt_script.get_main_session()
    # Run script's main logic against our session
    script_main(crt_session)
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Get a simulated session object to pass into the script.
    sim_session = direct_script.get_main_session()
    # Run script's main logic against our session
    script_main(sim_session)
    # Shutdown logging after
    logging.shutdown()
