# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will grab the detailed CDP information from a Cisco IOS or NX-OS device and create SecureCRT sessions
# based on the information, making it easier to manually crawl through a new network.
# 
#

# TODO: Create a settings file to specify the session directory

# ##############################  SCRIPT SETTING  ###############################
#
# Other Settings for this script are saved in the "script_settings.json" file that should be located in the same
# directory as this script.
#


# #################################  IMPORTS  ##################################
# Import OS and Sys module to be able to perform required operations for adding the script directory to the python
# path (for loading modules), and manipulating paths for saving files.
import os
import sys

# Add the script directory to the python path (if not there) so we can import custom modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Imports from custom SecureCRT modules
from imports.cisco_securecrt import start_session
from imports.cisco_securecrt import end_session
from imports.cisco_securecrt import get_output
from imports.cisco_securecrt import create_session

from imports.cisco_tools import textfsm_parse_to_list
from imports.cisco_tools import extract_system_name



##################################  SCRIPT  ###################################


def create_sessions_from_cdp(session, cdp_list):
    for device in cdp_list:
        # Extract hostname and IP to create session
        system_name = device[2]

        # If we couldn't get a System name, use the device ID
        if system_name == "":
            system_name = device[1]

        mgmt_ip = device[7]
        if mgmt_ip == "":
            if device[4] == "":
                # If no mgmt IP or interface IP, skip device.
                continue
            else:
                mgmt_ip = device[4]

        # Create a new session from the default information.
        create_session(session, system_name, mgmt_ip)


def main():
    """
    Capture the CDP information from the connected device and ouptut it into a CSV file. 
    """
    send_cmd = "show cdp neighbors detail"

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Make sure we completed session start.  If not, we'll receive None from start_session.
    if session:
        # Capture output from show cdp neighbor detail
        raw_cdp_list = get_output(session, send_cmd)

        # Parse CDP information into a list of lists.
        # TextFSM template for parsing "show cdp neighbor detail" output
        cdp_template = "textfsm-templates/show-cdp-detail"
        # Build path to template, process output and export to CSV
        template_path = os.path.join(script_dir, cdp_template)

        # Use TextFSM to parse our output
        cdp_table = textfsm_parse_to_list(raw_cdp_list, template_path, add_header=True)

        # Since "System Name" is a newer N9K feature -- try to extract it from the device ID when its empty.
        for entry in cdp_table:
            # entry[2] is system name, entry[1] is device ID
            if entry[2] == "":
                entry[2] = extract_system_name(entry[1])

        create_sessions_from_cdp(session, cdp_table)

        # Clean up before exiting
        end_session(session)


if __name__ == "__builtin__":
    main()