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
from imports.py_utils import human_sort_key


##################################  SCRIPT  ###################################


def extract_cdp_data(raw_cdp):

    # TextFSM template for parsing "show cdp neighbor detail" output.  Must supply TextFSM template and output string.
    cdp_template = "textfsm-templates/show-cdp-detail"
    # Build path to template, process output and export to CSV
    template_path = os.path.join(script_dir, cdp_template)
    cdp_table = parse_with_textfsm(raw_cdp, template_path)

    cdp_data = {}
    found_intfs = set()

    # Loop through all entry, excluding header row
    for entry in cdp_table[1:]:
        local_intf = entry[0]
        device_id = entry[1]
        system_name = entry[2]
        remote_intf = entry[3]
        if system_name == "":
            system_name = extract_system_name(device_id)

        # 7Ks can give multiple CDP entries when VDCs share the mgmt0 port.  If duplicate name is found, remove it
        if local_intf in found_intfs:
            # Remove from our description list
            cdp_data.pop(system_name, None)
        else:
            cdp_data[local_intf] = (system_name, short_int(remote_intf))
            found_intfs.add(local_intf)

    return cdp_data


# def add_port_channels(desc_data):
#     pass


def main():
    """
    Capture the CDP information from the connected device and ouptut it into a CSV file. 
    """
    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Capture output from show cdp neighbor detail
    raw_cdp_output = get_output(session, "show cdp neighbors detail")

    description_data = extract_cdp_data(raw_cdp_output)

    #TODO Add descriptions for port-channels where possible.
    # # Capture port-channel output
    # if session['OS'] == "NX-OS":
    #     raw_pc_output = get_output(session, "show port-channel summary")
    # elif "IOS" in session['OS']:
    #     raw_pc_output = get_output(session, "show etherchannel summary")
    # else:
    #     raw_pc_output = ""
    #
    # add_port_channels(description_data)

    # This will contain our configuration commands as CDP neighbors are found.
    config_script = ""
    # Generate a string of config commands to apply interface descriptions
    intf_list = sorted(description_data.keys(), key=human_sort_key)
    for interface in intf_list:
        config_script += "interface {}\n".format(interface)
        config_script += "  description {}, {}\n".format(description_data[interface][0], description_data[interface][1])

    output_filename = create_output_filename(session, "intf-desc", include_date=False)
    with open(output_filename, 'wb') as output_file:
        output_file.write(config_script)

    # Clean up before exiting
    end_session(session)


if __name__ == "__builtin__":
    main()