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

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ##################################################

def script_main(script):
    """
    | MULTIPLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will pull the ARP tables from multiple devices and combine their data into a single ARP table.  This may
    be useful when there are 2 core devices that are running in some sort of active/active configuration, or when you
    need a merged ARP table from multiple devices and VRFs to fully map every device attached to a particular switch.

    NOTE: Since this script merges the ARP tables of multiple devices which may have duplicate entries, the interface
          parameter is NOT written to the output file.

    This script checks that it will NOT be run in a connected tab.  This script initiates the connection to all devices
    based on the input of the device CSV file that the script requests.

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

    # Prompt for the VRF
    selected_vrf = script.prompt_window("Enter the VRF name.\n(Leave blank for default VRF)")
    if selected_vrf == "":
        selected_vrf = None
    logger.debug("Set VRF to '{0}'".format(selected_vrf))

    # Check settings if we should use a proxy/jumpbox
    use_proxy = script.settings.getboolean("Global", "use_proxy")
    default_proxy_session = script.settings.get("Global", "proxy_session")

    # ########################################  START DEVICE CONNECT LOOP  ###########################################

    # Create a filename to keep track of our connection logs, if we have failures.  Use script name without extension
    failed_log = session.create_output_filename("{0}-LOG".format(script_name.split(".")[0]), include_hostname=False)

    arp_collection = []

    for device in device_list:
        hostname = device['hostname']
        protocol = device['protocol']
        username = device['username']
        password = device['password']
        enable = device['enable']
        proxy = device['proxy']

        if not proxy and use_proxy:
            proxy = default_proxy_session

        logger.debug("<M_SCRIPT> Connecting to {0}.".format(hostname))
        try:
            session.connect(hostname, username, password, protocol=protocol, proxy=proxy)
            arp_collection.extend(per_device_work(session, selected_vrf, add_header=False))
            session.disconnect()
        except sessions.ConnectError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("Connect to {0} failed: {1}\n".format(hostname, e.message.strip()))
        except sessions.InteractionError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("Failure on {0}: {1}\n".format(hostname, e.message.strip()))

    # #########################################  END DEVICE CONNECT LOOP  ############################################

    # #########################################  PROCESS COLLECTED DATA  #############################################

    # Build a combined table without duplicate values from the data retrieved from all devices.
    combined_table = []
    seen = set()
    for entry in arp_collection:
        if entry[2] not in seen:
            combined_table.append([entry[0], "", entry[2], entry[3], ""])
            seen.add(entry[2])
    combined_table.sort(key=lambda x: utilities.human_sort_key(x[0]))
    combined_table.insert(0, ["IP ADDRESS", "", "MAC ADDRESS", "VLAN", ""])

    # Generate filename and output data as CSV
    output_filename = session.create_output_filename("merged-arp", include_hostname=False, ext=".csv")
    utilities.list_of_lists_to_csv(combined_table, output_filename)


def per_device_work(session, selected_vrf, add_header):
    """
    This function contains the code that should be executed on each device that this script connects to.  It is called
    after establishing a connection to each device in the loop above.

    This function gathers the ARP table information and returns it (in list format) to the calling program.
    """
    script = session.script
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["IOS", "NXOS"])

    # Select template file based on network OS
    if session.os == "IOS":
        send_cmd = "show ip arp"
        template_file = script.get_template("cisco_ios_show_ip_arp.template")
    else:
        send_cmd = "show ip arp detail"
        template_file = script.get_template("cisco_nxos_show_ip_arp_detail.template")

    # If a VRF was specified, update the commands and outputs to reflect this.
    if selected_vrf:
        send_cmd = send_cmd + " vrf {0}".format(selected_vrf)
        script.hostname = script.hostname + "-VRF-{0}".format(selected_vrf)
        logger.debug("Updated hostname to: '{0}'".format(script.hostname))

    # Get "show ip arp" data
    raw_arp = session.get_command_output(send_cmd)

    # Process with TextFSM
    logger.debug("Using template: '{0}'".format(template_file))
    fsm_results = utilities.textfsm_parse_to_list(raw_arp, template_file, add_header=add_header)

    # Return terminal parameters to starting values
    session.end_cisco_session()

    return fsm_results


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