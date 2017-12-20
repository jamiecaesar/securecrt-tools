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

    This script will grab the detailed CDP information from a Cisco IOS or NX-OS device and export it to a CSV file
    containing the important information, such as Remote Device hostname, model and IP information, in addition to the
    local and remote interfaces that connect the devices.

    | Script Settings (found in settings/settings.ini):
    | strip_domains -  A list of domain names that will be stripped away if found in the CDP remote device name.

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

    # Define the command to send to the remote device
    send_cmd = "show cdp neighbors detail"
    logger.debug("Command set to '{0}'".format(send_cmd))

    # Get domain names to strip from device IDs from settings file
    strip_list = script.settings.getlist("cdp_to_csv", "strip_domains")

    # Get the output from our above command
    raw_cdp = session.get_command_output(send_cmd)

    # Choose the TextFSM template and process the data
    template_file = script.get_template("cisco_os_show_cdp_neigh_det.template")
    fsm_results = utilities.textfsm_parse_to_list(raw_cdp, template_file, add_header=True)

    # Since "System Name" is a newer NXOS feature -- try to extract it from the device ID when its empty.
    for entry in fsm_results:
        # entry[2] is system name, entry[1] is device ID
        if entry[2] == "":
            entry[2] = utilities.extract_system_name(entry[1], strip_list=strip_list)

    output_filename = session.create_output_filename("cdp", ext=".csv")
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
