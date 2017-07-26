# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will capture the ARP table of the attached device and output the results as a CSV file.  While this
# script can be used to capture the ARP table, the primary purpose is to create the ARP associations that the
# "connected_ip.py" script can use to map which MAC and IP addresses are connected to each device.
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
from imports.cisco_securecrt import get_output
from imports.cisco_securecrt import write_output_to_file
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import list_of_lists_to_csv

from imports.cisco_tools import textfsm_parse_to_list



# #################################  SCRIPT  ###################################


def main():
    """
    Capture the ARP information from the connected device and ouptut it to a CSV file. 
    """
    supported_os = ["IOS", "NX-OS"]

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Make sure we completed session start.  If not, we'll receive None from start_session.
    if session:
        if session['OS'] not in supported_os:
            crt.Dialog.Messagebox("This device OS is not supported by this script.  Exiting.")
            return

        if session['OS'] == "IOS":
            send_cmd = "show ip arp"
            arp_template = "textfsm-templates/cisco_ios_show_ip_arp.template"
        else:
            send_cmd = "show ip arp detail"
            arp_template = "textfsm-templates/cisco_nxos_show_ip_arp_detail.template"

        # Capture output from show cdp neighbor detail
        temp_filename = create_output_filename(session, "arp")
        write_output_to_file(session, send_cmd, temp_filename)
        # raw_arp_list = get_output(session, send_cmd)

        # Build full path to template
        template_path = os.path.join(script_dir, arp_template)

        # Use TextFSM to parse our output from the temporary file, and delete it.
        with open(temp_filename, 'r') as arp_file:
            raw_arp_list=arp_file.read()
            arp_table = textfsm_parse_to_list(raw_arp_list, template_path, add_header=True)
        os.remove(temp_filename)

        # Write TextFSM output to a .csv file.
        output_filename = create_output_filename(session, "arp", ext=".csv")
        list_of_lists_to_csv(session, arp_table, output_filename)

        # Clean up before exiting
        end_session(session)


if __name__ == "__builtin__":
    main()