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

def script_main(script):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will grab the MAC address table from a Cisco IOS or NX-OS device and export it to a CSV file.

    :param script: A subclass of the scripts.Script object that represents the execution of this particular script
                   (either CRTScript or DirectScript)
    :type script: scripts.Script
    """
    # Get session object that interacts with the SecureCRT tab from where this script was launched
    session = script.get_main_session()

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["IOS", "NXOS"])

    # TextFSM template for parsing "show mac address-table" output
    if session.os == "NXOS":
        template_file = script.get_template("cisco_nxos_show_mac_addr_table.template")
    else:
        template_file = script.get_template("cisco_ios_show_mac_addr_table.template")

    raw_mac = session.get_command_output("show mac address-table")
    fsm_results = utilities.textfsm_parse_to_list(raw_mac, template_file, add_header=True)

    # Check if IOS mac_table is empty -- if so, it is probably because the switch has an older IOS
    # that expects "show mac-address-table" instead of "show mac address-table".
    if session.os == "IOS" and len(fsm_results) == 1:
        send_cmd = "show mac-address-table dynamic"
        logger.debug("Retrying with command set to '{0}'".format(send_cmd))
        raw_mac = session.get_command_output(send_cmd)
        fsm_results = utilities.textfsm_parse_to_list(raw_mac, template_file, add_header=True)

    output_filename = session.create_output_filename("mac-addr", ext=".csv")
    utilities.list_of_lists_to_csv(fsm_results, output_filename)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_script = scripts.CRTScript(crt)
    script_main(crt_script)
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_script = scripts.DirectScript(os.path.realpath(__file__))
    script_main(direct_script)
    logging.shutdown()