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
from securecrt_tools import script_types
from securecrt_tools import utilities

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(session):
    """
    Author: Jamie Caesar
    Email: jcaesar@presidio.com

    This script will capture the ARP table of the attached device and output the results as a CSV file.  While this
    script can be used to capture the ARP table, the primary purpose is to create the ARP associations that the
    "connected_ip.py" script can use to map which MAC and IP addresses are connected to each device.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type session: script_types.Script
    """
    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    supported_os = ["IOS", "NXOS"]
    if session.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Raising exception.".format(session.os))
        raise script_types.UnsupportedOSError("Remote device running unsupported OS: {0}.".format(session.os))

    # Prompt for the VRF
    selected_vrf = session.prompt_window("Enter the VRF name.\n(Leave blank for default VRF)")
    if selected_vrf == "":
        selected_vrf = None
    logger.debug("Set VRF to '{0}'".format(selected_vrf))

    # Select template file based on network OS
    if session.os == "IOS":
        send_cmd = "show ip arp"
        template_file = session.get_template("cisco_ios_show_ip_arp.template")
    else:
        send_cmd = "show ip arp detail"
        template_file = session.get_template("cisco_nxos_show_ip_arp_detail.template")

    logger.debug("Command set to '{0}'".format(send_cmd))

    # If a VRF was specified, update the commands and outputs to reflect this.
    if selected_vrf:
        send_cmd = send_cmd + " vrf {0}".format(selected_vrf)
        session.hostname = session.hostname + "-VRF-{0}".format(selected_vrf)
        logger.debug("Updated hostname to: '{0}'".format(session.hostname))

    # Get "show ip arp" data
    raw_arp = session.get_command_output(send_cmd)

    # Process with TextFSM
    logger.debug("Using template: '{0}'".format(template_file))
    fsm_results = utilities.textfsm_parse_to_list(raw_arp, template_file, add_header=True)

    # Generate filename and output data as CSV
    output_filename = session.create_output_filename("arp", ext=".csv")
    utilities.list_of_lists_to_csv(fsm_results, output_filename)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_session = script_types.CRTScript(crt)
    script_main(crt_session)

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_session = script_types.DirectScript(os.path.realpath(__file__))
    script_main(direct_session)