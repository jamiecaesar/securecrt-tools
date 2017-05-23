# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will grab the MAC address table from a Cisco IOS or NX-OS device and export it to a CSV file.
# 
#


# ##############################  SCRIPT SETTING  ###############################
#
# Settings for this script are saved in the "script_settings.json" file that should be located in the same directory as
# this script.
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
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import get_output
from imports.cisco_tools import parse_with_textfsm
from imports.py_utils import list_of_lists_to_csv

##################################  SCRIPT  ###################################


def main():
    """
    Capture the CDP information from the connected device and ouptut it into a CSV file. 
    """
    send_cmd = "show mac address-table"

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)
    settings = session['settings']

    # Capture output from show cdp neighbor detail
    raw_mac_list = get_output(session, send_cmd)

    # TextFSM template for parsing "show mac address-table" output
    if settings['OS'] == "NX-OS":
        mac_template = "textfsm-templates/show-mac-addr-table-nxos"
    else:
        mac_template = "textfsm-templates/show-mac-addr-table-ios"

    # Parse MAC information into a list of lists.
    # Build path to template, process output and export to CSV
    template_path = os.path.join(script_dir, mac_template)

    cdp_table = parse_with_textfsm(raw_mac_list, template_path)
    # Write TextFSM output to a .csv file.
    output_filename = create_output_filename(session, "mac-addr", ext=".csv")
    list_of_lists_to_csv(cdp_table, output_filename)

    # Clean up before exiting
    end_session(session)


if __name__ == "__builtin__":
    main()