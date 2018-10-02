# $language = "python"
# $interface = "1.0"

import os
import sys
import logging

# Add script directory to the PYTHONPATH so we can import our modules (only if run from SecureCRT)
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))

# Now we can import our custom modules
from securecrt_tools import scripts
from securecrt_tools import sessions
from securecrt_tools import utilities
# Import message box constants names for use specifying the design of message boxes
from securecrt_tools.message_box_const import *
from s_document_device import document

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ##################################################

def script_main(script):
    """
    | MULTIPLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will grab the output for a list of commands from the provided list of devices.  The list of commands is
    taken from the 'settings/settings.ini' file.  There is a separate list for each supported network operating system
    (IOS, NXOS and ASA) and by default the list that matches the network operating system of the connected device will
    be used.

    Custom lists of commands are supported.  These lists can be added manually to the [document_device] section of the
    'settings/settings.ini' file.  To be able to choose one of these lists when running the script, the
    'prompt_for_custom_lists' setting needs to be changed to 'True' in the settings.ini file.  Once this option is
    enabled, the script will prompt for the name of the list that you want to use.  If the input is left blank then
    the default behavior (based on network OS) will choose the list.

    NOTE:
    The Custom list can be set on a PER DEVICE basis if a column names "Command List" (case sensitive) is added to the
    device list CSV file that is selected when running this script.  If the "Command List" column is missing or the
    field is left blank for a device then the list will be chosen using the default behavior (i.e. use the list
    specified when running the script, or based on the network OS of each device).

    | Script Settings (found in settings/settings.ini):
    | show_instructions - When True, displays a pop-up upon launching the script explaining where to modify the list of
    |   commands sent to devices.  This window also prompts the user if they want to continue seeing this message.  If
    |   not, the script changes this setting to False.
    | folder_per_device - If True, Creates a folder for each device, based on the hostname, and saves all files inside
    |   that folder WITHOUT the hostname in the output file names.  If False, it saves all the files directly into the
    |   output folder from the global settings and includes the hostname in each individual filename.
    | prompt_for_custom_lists - When set to True, the script will prompt the user to type the name of a list of
    |   commands to use with the connected device.  This list name must be found as an option in the [document_device]
    |   section of the settings.ini file.  The format is the same as the default network OS lists, 'ios', 'nxos', etc.
    | ios - The list of commands that will be run on IOS devices
    | nxos - The list of commands that will be run on NXOS devices
    | asa - The list of commands that will be run on ASA devices

    Any additional options found in this section would be custom added by the user and are expected to be lists of
    commands for use with the 'prompt_for_custom_lists' setting.

    By default, The outputs will be saved in a folder named after the hostname of the device, with each output file
    being saved inside that directory.  This behavior can be changed in the settings above.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session
    """
    session = script.get_main_session()

    # If this is launched on an active tab, disconnect before continuing.
    logger.debug("<M_SCRIPT> Checking if current tab is connected.")
    if session.is_connected():
        logger.debug("<M_SCRIPT> Existing tab connected.  Stopping execution.")
        raise scripts.ScriptError("This script must be launched in a not-connected tab.")

    # Load a device list
    device_list = script.import_device_list()
    if not device_list:
        return

    # Check settings if we should use a proxy/jumpbox
    use_proxy = script.settings.getboolean("Global", "use_proxy")
    default_proxy_session = script.settings.get("Global", "proxy_session")

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
        default_command_list = script.prompt_window(
            "Enter the name of the command list you want to use.\n\nThese lists are found "
            "in the [document_device] section of your settings.ini file\n",
            "Enter command list")
    else:
        default_command_list = None

    folder_per_device = script.settings.getboolean("document_device", "folder_per_device")

    # ########################################  START DEVICE CONNECT LOOP  ###########################################

    # Create a filename to keep track of our connection logs, if we have failures.  Use script name without extension
    failed_log = session.create_output_filename("{0}-LOG".format(script_name.split(".")[0]), include_hostname=False)

    for device in device_list:
        hostname = device['Hostname']
        protocol = device['Protocol']
        username = device['Username']
        password = device['Password']
        enable = device['Enable']
        try:
            proxy = device['Proxy Session']
        except KeyError:
            proxy = None
        try:
            if device['Command List']:
                command_list = device['Command List']
            else:
                command_list = default_command_list
        except KeyError:
            command_list = default_command_list

        if not proxy and use_proxy:
            proxy = default_proxy_session

        logger.debug("<M_SCRIPT> Connecting to {0}.".format(hostname))
        try:
            session.connect(hostname, username, password, protocol=protocol, proxy=proxy)
            per_device_work(session, command_list, folder_per_device)
            session.disconnect()
        except sessions.ConnectError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("Connect to {0} failed: {1}\n".format(hostname, e.message.strip()))
                session.disconnect()
        except sessions.InteractionError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("Failure on {0}: {1}\n".format(hostname, e.message.strip()))
                session.disconnect()
        except sessions.UnsupportedOSError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("Unsupported OS on {0}: {1}\n".format(hostname, e.message.strip()))
                session.disconnect()

    # #########################################  END DEVICE CONNECT LOOP  ############################################


def per_device_work(session, command_list_name, folder_per_device):
    """
    This function contains the code that should be executed on each device that this script connects to.  It is called
    after establishing a connection to each device in the loop above.

    This function simply calls the imported "document()" function from the s_document_device script on each device
    connected to.
    """
    session.start_cisco_session()

    # Document scripts according to settings captures above.  If we want folder_per_device, don't include hostname in
    # the filename and vice versa.
    document(session, command_list_name, folder_per_device, prompt_create_dirs=False)

    session.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Run script's main logic against the script object
    script_main(crt_script)
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Run script's main logic against the script object
    script_main(direct_script)
    # Shutdown logging after
    logging.shutdown()