# $language = "python"
# $interface = "1.0"

import os
import sys
import logging
import csv

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
    | Morphed: Gordon Rogier grogier@cisco.com
    | Framework: Jamie Caesar jcaesar@presidio.com

    This script will

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["AireOS"])

    # Get additional information we'll need
    info_list = get_interface_detail(session)

    output_filename = session.create_output_filename("interface-detail", ext=".csv")
    utilities.list_of_lists_to_csv(info_list, output_filename)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


def get_interface_detail(session):
    """
    A function that captures the WLC AireOS interface detail table and returns an output list

    :param session: The script object that represents this script being executed
    :type session: session.Session

    :return: A list of MAC information for AP summary
    :rtype: list
    """
    send_cmd = "show interface summary"
    output_raw = session.get_command_output(send_cmd)

    # TextFSM template for parsing "show interface summary" output
    template_file = session.script.get_template("cisco_aireos_show_interface_summary.template")
    interface_summ_dict = utilities.textfsm_parse_to_dict(output_raw, template_file)

    output_raw = ''
    for interface_entry in interface_summ_dict:
        send_cmd = "show interface detailed " + format(interface_entry["INT_Name"])
        output_raw += session.get_command_output(send_cmd)

    # TextFSM template for parsing "show interface detailed <interface-name>" output
    template_file = session.script.get_template("cisco_aireos_show_interface_detailed.template")
    output = utilities.textfsm_parse_to_list(output_raw, template_file, add_header=True)

    return output


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Get session object for the SecureCRT tab that the script was launched from.
    crt_session = crt_script.get_main_session()
    # Run script's main logic against our session
    try:
        script_main(crt_session)
    except Exception:
        crt_session.end_cisco_session()
        raise
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
