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
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(session):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will output the VLAN database to a CSV file.

    One possibly use of this script is to take the .CSV outputs from 2 or more devices, paste them
    into a single XLS file and use Excel to highlight duplicate values, so VLAN overlaps can be
    discovered prior to connecting switches together via direct link, OTV, etc.  This could also be used
    to find missing VLANs between 2 large tables that should have the same VLANs.

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

    if session.os == "IOS":
        template_file = script.get_template("cisco_ios_show_vlan.template")
    else:
        template_file = script.get_template("cisco_nxos_show_vlan.template")

    raw_vlan = session.get_command_output("show vlan brief")

    fsm_results = utilities.textfsm_parse_to_list(raw_vlan, template_file, add_header=True)

    normalize_port_list(fsm_results)

    output_filename = session.create_output_filename("vlan", ext=".csv")
    utilities.list_of_lists_to_csv(fsm_results, output_filename)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


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
