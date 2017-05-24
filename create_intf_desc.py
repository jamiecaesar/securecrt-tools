# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will grab the detailed CDP information from a Cisco IOS or NX-OS device and output a text file containing
# the configuration scripts to label all the interfaces found in the CDP table.
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
from imports.cisco_tools import extract_system_name
from imports.cisco_tools import short_int


##################################  SCRIPT  ###################################


def main():
    """
    Capture the CDP information from the connected device and ouptut it into a CSV file. 
    """
    send_cmd = "show cdp neighbors detail"

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Capture output from show cdp neighbor detail
    raw_cdp_list = get_output(session, send_cmd)

    # TextFSM template for parsing "show cdp neighbor detail" output.  Must supply TextFSM template and output string.
    cdp_template = "textfsm-templates/show-cdp-detail"
    # Build path to template, process output and export to CSV
    template_path = os.path.join(script_dir, cdp_template)
    cdp_table = parse_with_textfsm(raw_cdp_list, template_path)

    # This will contain our configuration commands as CDP neighbors are found.
    config_script = ""

    # Generate a string of config commands to apply interface descriptions
    for entry in cdp_table:
        local_intf = entry[0]
        device_id = entry[1]
        system_name = entry[2]
        remote_intf = entry[3]
        if system_name == "":
            system_name = extract_system_name(device_id)
        config_script += "interface {}\n".format(local_intf)
        config_script += "  description {}, {}\n".format(system_name, short_int(remote_intf))

    output_filename = create_output_filename(session, "intf-desc", include_date=False)
    with open(output_filename, 'wb') as output_file:
        output_file.write(config_script)

    # Clean up before exiting
    end_session(session)


if __name__ == "__builtin__":
    main()