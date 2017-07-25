# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# This script will scrape some stats (packets, rate, errors) from all the UP interfaces on the device and put it into
# a CSV file.
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

# Imports from Cisco SecureCRT library
from imports.cisco_securecrt import ICON_STOP
from imports.cisco_securecrt import start_session
from imports.cisco_securecrt import end_session
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import get_output
from imports.cisco_securecrt import list_of_lists_to_csv

from imports.cisco_tools import textfsm_parse_to_list


##################################  SCRIPT  ###################################


def main():
    send_cmd = "show interface"
    SupportedOS = ["IOS", "IOS XE", "NX-OS"]

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Make sure we completed session start.  If not, we'll receive None from start_session.
    if session:
        raw_intf_output = get_output(session, send_cmd)

        if session['OS'] in SupportedOS:
            if session['OS'] == "NX-OS":
                interface_template = "textfsm-templates/show-interfaces-nxos"
            else:
                interface_template = "textfsm-templates/show-interfaces-ios"
        else:
            interface_template = None
            error_str = "This script does not support {}.\n" \
                        "It will currently only run on {}.".format(session['OS'], ", ".join(SupportedOS))
            crt.Dialog.MessageBox(error_str, "Unsupported Network OS", ICON_STOP)

        if interface_template:
            # Generate filename used for output files.
            output_filename = create_output_filename(session, "show-interfaces", ext=".csv")
            # Build path to template, process output and export to CSV
            template_path = os.path.join(script_dir, interface_template)
            interface_stats = textfsm_parse_to_list(raw_intf_output, template_path, add_header=True)
            list_of_lists_to_csv(session, interface_stats, output_filename)

        end_session(session)


if __name__ == "__builtin__":
    main()
