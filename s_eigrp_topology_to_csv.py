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

def script_main(session, ask_vrf=True, vrf=None):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will grab the EIGRP topology table from a Cisco IOS or NXOS device and export it as a CSV file.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session
    :param ask_vrf: A boolean that specifies if we should prompt for which VRF.  The default is true, but when this
        module is called from other scripts, we may want avoid prompting and supply the VRF with the "vrf" input.
    :type ask_vrf: bool
    :param vrf: The VRF that we should get the route table from.  This is used only when ask_vrf is False.
    :type vrf: str
    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["IOS", "NXOS"])

    # If we should prompt for a VRF, then do so.  Otherwise use the VRF passed into the function (if any)
    if ask_vrf:
        selected_vrf = script.prompt_window("Enter the VRF name. (Leave blank for default VRF, 'all' for all VRFs)")
        logger.debug("Input VRF: {0}".format(selected_vrf))
    else:
        selected_vrf = vrf
        logger.debug("Received VRF: {0}".format(selected_vrf))

    # If we have a VRF, modify our commands and hostname to reflect it.  If not, pull the default route table.
    if selected_vrf:
        if session.os == "IOS":
            if selected_vrf == "all":
                send_cmd = "show ip eigrp vrf * topology"
                session.hostname = session.hostname + "-VRF-all".format(selected_vrf)
            else:
                send_cmd = "show ip eigrp vrf {0} topology".format(selected_vrf)
                session.hostname = session.hostname + "-VRF-{0}".format(selected_vrf)
        else:
            send_cmd = "show ip eigrp topology vrf {0}".format(selected_vrf)
            session.hostname = session.hostname + "-VRF-{0}".format(selected_vrf)
    else:
        send_cmd = "show ip eigrp topology"

    logger.debug("Generated Command: {0}".format(send_cmd))

    raw_topo = session.get_command_output(send_cmd)

    if session.os == "IOS":
        template_file = script.get_template("cisco_ios_show_ip_eigrp_topology.template")
    else:
        template_file = script.get_template("cisco_nxos_show_ip_eigrp_topology.template")

    fsm_results = utilities.textfsm_parse_to_list(raw_topo, template_file, add_header=True)

    output_filename = session.create_output_filename("eigrp-topo", ext=".csv")
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
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Get a simulated session object to pass into the script.
    sim_session = direct_script.get_main_session()
    # Run script's main logic against our session
    script_main(sim_session)
    # Shutdown logging after
    logging.shutdown()
