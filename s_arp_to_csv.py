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
from securecrt_tools import utilities

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(session):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will capture the ARP table of the attached device and output the results as a CSV file.  While this
    script can be used to capture the ARP table, the primary purpose is to create the ARP associations that the
    "s_switchport_mapping.py" script can use to map which MAC and IP addresses are connected to each device.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["IOS", "NXOS"])

    # Prompt for the VRF
    selected_vrf = script.prompt_window("Enter the VRF name.\n(Leave blank for default VRF)")
    if selected_vrf == "":
        selected_vrf = None
    logger.debug("Set VRF to '{0}'".format(selected_vrf))

    # Select template file based on network OS
    if session.os == "IOS":
        send_cmd = "show ip arp"
        template_file = script.get_template("cisco_ios_show_ip_arp.template")
    else:
        send_cmd = "show ip arp detail"
        template_file = script.get_template("cisco_nxos_show_ip_arp_detail.template")

    logger.debug("Command set to '{0}'".format(send_cmd))

    # If a VRF was specified, update the commands and outputs to reflect this.
    if selected_vrf:
        send_cmd = send_cmd + " vrf {0}".format(selected_vrf)
        script.hostname = script.hostname + "-VRF-{0}".format(selected_vrf)
        logger.debug("Updated hostname to: '{0}'".format(script.hostname))

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
    direct_script = scripts.DirectScript(os.path.realpath(__file__))
    # Get a simulated session object to pass into the script.
    sim_session = direct_script.get_main_session()
    # Run script's main logic against our session
    script_main(sim_session)
    # Shutdown logging after
    logging.shutdown()
