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
from imports.cisco_securecrt import get_output
from imports.cisco_securecrt import write_output_to_file

from imports.cisco_tools import get_template_full_path
from imports.cisco_tools import textfsm_parse_to_list
from imports.cisco_tools import extract_system_name
from imports.cisco_tools import short_int_name
from imports.cisco_tools import long_int_name

from imports.py_utils import human_sort_key


##################################  SCRIPT  ###################################


def extract_cdp_data(cdp_table):
    """
    Extract remote host and interface for each local interface in the CDP table
    
    :param cdp_table:  The TextFSM output for CDP neighbor detail 
    :return:  A dictionary for each local interface with corresponding remote host and interface.
    """
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
            cdp_data[local_intf] = (system_name, remote_intf)
            found_intfs.add(local_intf)

    return cdp_data


def add_port_channels(desc_data, pc_data):

    for entry in pc_data:
        po_name = entry[0]
        intf_list = entry[4]
        neighbor_set = set()
        # For each index in the intf_list
        for intf in intf_list:
            long_name = long_int_name(intf)
            if long_name in desc_data:
                neighbor_set.add(desc_data[long_name][0])
        if len(neighbor_set) > 0:
            desc_data[po_name] = list(neighbor_set)


def main():
    """
    Capture the CDP information from the connected device and ouptut it into a CSV file. 
    """
    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Make sure we completed session start.  If not, we'll receive None from start_session.
    if session:
        send_cmd = "show cdp neighbors detail"

        # Build full path to TextFSM template for parsing "show cdp neighbor detail" output.
        cdp_template = "cisco_os_show_cdp_neigh_det.template"
        template_path = get_template_full_path(session, cdp_template)

        # Capture output from our command and write to a temporary file
        temp_filename = create_output_filename(session, "cdp")
        write_output_to_file(session, send_cmd, temp_filename)

        # Use TextFSM to parse our output from the temporary file, and delete it.
        with open(temp_filename) as cdp_data:
            cdp_table = textfsm_parse_to_list(cdp_data, template_path, add_header=True)
        os.remove(temp_filename)

        # Get information required to build descriptions from CDP data
        description_data = extract_cdp_data(cdp_table)

        # Capture port-channel output
        if session['OS'] == "NX-OS":
            raw_pc_output = get_output(session, "show port-channel summary")
            pc_template = "cisco_nxos_show_portchannel_summary.template"
            pc_template_path = get_template_full_path(session, pc_template)
            pc_table = textfsm_parse_to_list(raw_pc_output, pc_template_path, add_header=True)
            add_port_channels(description_data, pc_table)
        elif "IOS" in session['OS']:
            raw_pc_output = get_output(session, "show etherchannel summary")
            pc_template = "cisco_ios_show_etherchannel_summary.template"
            pc_template_path = get_template_full_path(session, pc_template)
            pc_table = textfsm_parse_to_list(raw_pc_output, pc_template_path, add_header=True)
            add_port_channels(description_data, pc_table)
        else:
            pass


        # This will contain our configuration commands as CDP neighbors are found.
        config_script = ""
        # Generate a string of config commands to apply interface descriptions
        intf_list = sorted(description_data.keys(), key=human_sort_key)
        for interface in intf_list:
            config_script += "interface {}\n".format(interface)
            if "Po" in interface:
                neigh_list = description_data[interface]
                if len(neigh_list) == 1:
                    config_script += "  description {}\n".format(neigh_list[0])
                if len(neigh_list) == 2:
                    neigh_list = sorted(neigh_list, key=human_sort_key)
                    config_script += "  description vPC from {}, {}\n".format(neigh_list[0], neigh_list[1])
            else:
                config_script += "  description {}, {}\n".format(description_data[interface][0],
                                                                 short_int_name(description_data[interface][1]))

        output_filename = create_output_filename(session, "intf-desc", include_date=False)
        with open(output_filename, 'wb') as output_file:
            output_file.write(config_script)

        # Clean up before exiting
        end_session(session)


if __name__ == "__builtin__":
    main()