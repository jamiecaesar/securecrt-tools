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

def script_main(script):
    """
    SINGLE device script
    Author: Jamie Caesar
    Email: jcaesar@presidio.com

    This script will output the VLAN database to a CSV file.

    One possibly use of this script is to take the .CSV outputs from 2 or more devices, paste them
    into a single XLS file and use Excel to highlight duplicate values, so VLAN overlaps can be
    discovered prior to connecting switches together via direct link, OTV, etc.  This could also be used
    to find missing VLANs between 2 large tables that should have the same VLANs.

    :param script: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type script: script_types.Script
    """
    # Create logger instance so we can write debug messages (if debug mode setting is enabled in settings).
    logger = logging.getLogger("securecrt")
    logger.debug("Starting execution of {}".format(script_name))

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    script.start_cisco_session()

    # Validate device is running a supported OS
    supported_os = ["IOS", "NXOS"]
    if script.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Raising exception.".format(script.os))
        raise script_types.UnsupportedOSError("Remote device running unsupported OS: {0}.".format(script.os))

    send_cmd = "show vlan brief"
    if script.os == "IOS":
        template_file = script.get_template("cisco_ios_show_vlan.template")
    else:
        template_file = script.get_template("cisco_nxos_show_vlan.template")

    raw_vlan = script.get_command_output(send_cmd)

    fsm_results = utilities.textfsm_parse_to_list(raw_vlan, template_file, add_header=True)

    normalize_port_list(fsm_results)

    output_filename = script.create_output_filename("vlan", ext=".csv")
    utilities.list_of_lists_to_csv(fsm_results, output_filename)

    # Return terminal parameters back to the original state.
    script.end_cisco_session()


def normalize_port_list(vlan_data):
    """
    When TextFSM processes a VLAN with a long list of ports, each line will be a separate item in the resulting list.
    This fuction combines all of those entries into a single string that contains all of the ports in a comma-separated
    list.

    :param vlan_data: The VLAN data from TextFSM that will be modified in-place
    """
    # VLANs with multiple lines of Ports will have multiple list entries.  Combine all into a single string of ports.
    # Skip first (header) row
    for entry in vlan_data[1:]:
        port_list = entry[3]
        if len(port_list) > 0:
            port_string = ""
            for line in port_list:
                # Empty list entries contain a single entry.  Skip them.
                if line == " ":
                    continue
                # If port_string is still empty, add our line to this string.
                if port_string == "":
                    port_string = port_string + line
                # If there is something in port-string, concatenate strings with a ", " in between.
                else:
                    port_string = "{0}, {1}".format(port_string, line)
            entry[3] = port_string
        else:
            entry[3] = ""

# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_script = script_types.CRTScript(crt)
    script_main(crt_script)

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_script = script_types.DirectScript(os.path.realpath(__file__))
    script_main(direct_script)