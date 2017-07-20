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

# Imports from Cisco SecureCRT library
from imports.cisco_securecrt import ICON_STOP
from imports.cisco_securecrt import start_session
from imports.cisco_securecrt import end_session
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import get_output
from imports.cisco_tools import textfsm_parse_to_list
from imports.py_utils import list_of_lists_to_csv

##################################  SCRIPT  ###################################


def main():
    send_cmd = "show interface"
    SupportedOS = ["IOS", "IOS XE", "NX-OS"]

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

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
        list_of_lists_to_csv(interface_stats, output_filename)
    
    end_session(session)


if __name__ == "__builtin__":
    main()
