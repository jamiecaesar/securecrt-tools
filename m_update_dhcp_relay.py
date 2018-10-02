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
from s_update_dhcp_relay import build_valid_ip_list, update_helpers

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ##################################################

def script_main(script):
    """
    | MULTIPLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will scan the running configuration of the provided list of devices, looking for instances of old IP
    helper/DHCP relay addresses (IOS/NXOS) on interfaces and if found will update the helper/relay addresses with the
    newer ones. The new and old addresses that the script looks for is saved in the settings.ini file, as documented
    below.

    Any devices that cannot be connected to will be logged in a separate file saved in the output directory.

    This script will prompt you to run in "Check Mode", where the configuration changes the script would be pushed to
    the devices are ONLY written to a file and NO CHANGES will be made to the devices.  If you select "No" when prompted
    this script will push the configuration changes to the devices. Also, when the changes are pushed to the devices
    this script will save the running config before and after the changes are made, and will also output a log of the
    configuration sessions showing all the commands pushed.

    | Script Settings (found in settings/settings.ini):
    | show_instructions - When True, displays a pop-up upon launching the script explaining where to modify the list of
    |   commands sent to devices.  This window also prompts the user if they want to continue seeing this message.  If
    |   not, the script changes this setting to False.
    | old_relays - This is a comma separated list of IP addresses that the script should search for as relay addresses
    |   in the device's configuration.
    | new_relays - This is a comma separated list of IP addresses that are the new relay addresses that should be added
    |   to any interface that has at least one of the old helper/relay addresses on it.
    | remove_old_relays - If True, the script will add the new relays and REMOVE the old relays immediately after adding
    |   the new ones.  If False (default), the script will only add the new relays to interfaces where at least
    |   one old relay is found.  This is useful when you want to push out new relays as part of a migration process
    |   without removing the old relays.  Since this script will not try to push new relay addresses that already
    |   exist on an interface, the script can be run again with this option set to True to later remove the old relays.

    :param script: A subclass of the scripts.Script object that represents the execution of this particular script
                   (either CRTScript or DirectScript)
    :type script: scripts.Script
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

    # #########################################  GET VALUES FROM SETTINGS  ###########################################
    # Display instructions message, unless settings prevent it
    show_instructions = script.settings.getboolean("update_dhcp_relay", "show_instructions")
    if show_instructions:
        response = script.message_box("The list of old and new ip-helper/dhcp relay IPs can be edited in the "
                                      "'settings/settings.ini' file in the main securecrt-tools directory.\nSee the "
                                      "documentation for this script ('docs/index.html') for more details.\n\n"
                                      "Do you want to stop seeing this message?",
                                      "Instructions", ICON_QUESTION + BUTTON_YESNO)
        if response == IDYES:
            script.settings.update("update_dhcp_relay", "show_instructions", False)

    # Collection of old helpers/relays is in a set data structure to make membership checks easier.  A list works fine
    # for new helpers/relays.
    old_helpers = set(build_valid_ip_list(script.settings.getlist("update_dhcp_relay", "old_relays")))
    new_helpers = build_valid_ip_list(script.settings.getlist("update_dhcp_relay", "new_relays"))
    remove_old_helpers = script.settings.getboolean("update_dhcp_relay", "remove_old_relays")

    # #########################################  START CHECK MODE SECTION  ###########################################
    # Ask if this should be a test run (generate configs only) or full run (push updates to devices)
    # Comment out or remove the entire CHECK MODE SECTION if you don't want to prompt for check mode
    check_mode_message = "Do you want to run this script in check mode? (Only generate configs)\n" \
                         "\n" \
                         "Yes = Connect to device and write change scripts to a file ONLY\n" \
                         "No = Connect to device and PUSH configuration changes"
    message_box_design = ICON_QUESTION | BUTTON_YESNOCANCEL
    logger.debug("Prompting the user to run in check mode.")
    result = script.message_box(check_mode_message, "Run in Check Mode?", message_box_design)
    if result == IDYES:
        logger.debug("<M_SCRIPT> Received 'True' for Check Mode.")
        check_mode = True
    elif result == IDNO:
        logger.debug("<M_SCRIPT> Received 'False' for Check Mode.")
        check_mode = False
    else:
        return
    # ########################################### END CHECK MODE SECTION  ############################################

    # Check settings if we should use a proxy/jumpbox
    use_proxy = script.settings.getboolean("Global", "use_proxy")
    default_proxy_session = script.settings.get("Global", "proxy_session")

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

        if not proxy and use_proxy:
            proxy = default_proxy_session

        logger.debug("<M_SCRIPT> Connecting to {0}.".format(hostname))
        try:
            script.connect(hostname, username, password, protocol=protocol, proxy=proxy)
            session = script.get_main_session()
            per_device_work(session, check_mode, enable, old_helpers, new_helpers, remove_old_helpers)
            script.disconnect()
        except scripts.ConnectError as e:
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


def per_device_work(session, check_mode, enable_pass, old_helpers, new_helpers, remove_old_helpers):
    """
    This function contains the code that should be executed on each device that this script connects to.  It is called
    after establishing a connection to each device in the loop above.

    You can either put your own code here, or if there is a single-device version of a script that performs the correct
    task, it can be imported and called here, essentially making this script connect to all the devices in the chosen
    CSV file and then running a single-device script on each of them.
    """
    session.start_cisco_session(enable_pass=enable_pass)
    update_helpers(session, check_mode, old_helpers, new_helpers, remove_old_helpers)
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