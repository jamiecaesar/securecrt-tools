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
# Global settings that affect all scripts (output directory, date format, etc) is stored in the "global_settings.json"
# file in the "settings" directory.
#
# If any local settings are used for this script, they will be stored in the same settings folder, with the same name
# as the script that uses them, except ending with ".json".
#
# All settings can be manually modified with the same syntax as Python lists and dictionaries.   Be aware of required
# commas between items, or else options are likely to get run together and neither will work.
#
# **IMPORTANT**  All paths saved in .json files must contain either forward slashes (/home/jcaesar) or
# DOUBLE back-slashes (C:\\Users\\Jamie).   Single backslashes will be considered part of a control character and will
# cause an error on loading.
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
from imports.cisco_securecrt import write_output_to_file
from imports.cisco_securecrt import list_of_lists_to_csv

from imports.cisco_tools import get_template_full_path
from imports.cisco_tools import textfsm_parse_to_list


##################################  SCRIPT  ###################################


def main():
    """
    Capture the CDP information from the connected device and ouptut it into a CSV file. 
    """
    supported_os = ["IOS", "NX-OS"]
    send_cmd = "show mac address-table"

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Make sure we completed session start.  If not, we'll receive None from start_session.
    if session:
        if session['OS'] not in supported_os:
            crt.Dialog.Messagebox("This device OS is not supported by this script.  Exiting.")
            return

        # Capture output from show cdp neighbor detail
        temp_filename = create_output_filename(session, "mac-addr")
        write_output_to_file(session, send_cmd, temp_filename)

        # TextFSM template for parsing "show mac address-table" output
        if session['OS'] == "NX-OS":
            mac_template = "cisco_nxos_show_mac_addr_table.template"
        else:
            mac_template = "cisco_ios_show_mac_addr_table.template"

        # Build path to template, process output and export to CSV
        template_path = get_template_full_path(session, mac_template)

        # Parse MAC information into a list of lists.
        with open(temp_filename, 'r') as mac_data:
            mac_table = textfsm_parse_to_list(mac_data, template_path, add_header=True)
        os.remove(temp_filename)

        # Write TextFSM output to a .csv file.
        output_filename = create_output_filename(session, "mac-addr", ext=".csv")
        list_of_lists_to_csv(session, mac_table, output_filename)

        # Clean up before exiting
        end_session(session)


if __name__ == "__builtin__":
    main()