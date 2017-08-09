# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will first prompt for the location of the ARP table to use for processing.   Next, the mac address table
# of the active session will be captured and a CSV file showing the MAC address and IP of what is attached to each port
# on the device will be output.
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
import csv

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

from imports.cisco_tools import get_template_full_path
from imports.cisco_tools import textfsm_parse_to_list
from imports.cisco_tools import long_int_name

from imports.py_utils import human_sort_key


# #################################  SCRIPT  ###################################

def get_int_status(session):
    send_cmd = "show interface status"

    if session['OS'] == "NX-OS":
        int_template = "cisco_nxos_show_interface_status.template"
    else:
        int_template = "cisco_ios_show_interfaces_status.template"

    temp_filename = create_output_filename(session, "int-status")
    write_output_to_file(session, send_cmd, temp_filename)

    template_path = get_template_full_path(session, int_template)

    with open(temp_filename, 'r') as mac_data:
        int_table = textfsm_parse_to_list(mac_data, template_path, add_header=False)
    os.remove(temp_filename)

    for entry in int_table:
        entry[0] = long_int_name(entry[0])

    return int_table


def get_mac_table(session):
    # TextFSM template for parsing "show mac address-table" output
    if session['OS'] == "NX-OS":
        send_cmd = "show mac address-table"
        mac_template = "cisco_nxos_show_mac_addr_table.template"
    else:
        send_cmd = "show mac address-table"
        mac_template = "cisco_ios_show_mac_addr_table.template"

    temp_filename = create_output_filename(session, "mac-addr")
    write_output_to_file(session, send_cmd, temp_filename)

    template_path = get_template_full_path(session, mac_template)

    with open(temp_filename, 'r') as mac_data:
        mac_table = textfsm_parse_to_list(mac_data, template_path, add_header=False)
    os.remove(temp_filename)

    # Check if IOS mac_table is empty -- if so, it is probably because the switch has an older IOS
    # that expects "show mac-address-table" instead of "show mac address-table".
    if session['OS'] == "IOS" and len(mac_table) == 0:
        send_cmd = "show mac-address-table dynamic"

        temp_filename = create_output_filename(session, "mac-addr")
        write_output_to_file(session, send_cmd, temp_filename)

        template_path = get_template_full_path(session, mac_template)

        with open(temp_filename, 'r') as mac_data:
            mac_table = textfsm_parse_to_list(mac_data, template_path, add_header=False)
        os.remove(temp_filename)

    # Check for vPCs on NXOS to account for "vPC Peer-Link" entries in MAC table of N9Ks
    elif session['OS'] == "NX-OS":
        send_cmd = "show vpc"
        vpc_template = "cisco_nxos_show_vpc.template"

        temp_filename = create_output_filename(session, "vpc")
        write_output_to_file(session, send_cmd, temp_filename)

        template_path = get_template_full_path(session, vpc_template)

        with open(temp_filename, 'r') as vpc_data:
            vpc_table = textfsm_parse_to_list(vpc_data, template_path, add_header=False)
        os.remove(temp_filename)

        if len(vpc_table) > 0:
            peer_link_record = vpc_table[0]
            peer_link = long_int_name(peer_link_record[1])
        else:
            peer_link = None

    # Convert TextFSM output to a dictionary for lookups
    output = {}
    for entry in mac_table:
        vlan = entry[0]
        mac = entry[1]

        raw_intf = entry[2]
        if "vpc" in raw_intf.lower():
            intf = peer_link
        else:
            intf = long_int_name(raw_intf)

        if intf in output:
            output[intf].append((mac, vlan))
        else:
            output[intf] = [(mac, vlan)]

    return output


def get_desc_table(session):
    # TextFSM template for parsing "show mac address-table" output
    if session['OS'] == "NX-OS":
        send_cmd = "show interface description"
        desc_template = "cisco_nxos_show_interface_description.template"
    else:
        send_cmd = "show interface description"
        desc_template = "cisco_ios_show_interfaces_description.template"

    raw_desc_list = get_output(session, send_cmd)

    template_path = get_template_full_path(session, desc_template)

    desc_list = textfsm_parse_to_list(raw_desc_list, template_path, add_header=False)

    desc_table = {}
    # Change interface names to long versions for better matching with other outputs
    for entry in desc_list:
        intf = long_int_name(entry[0])
        desc_table[intf] = entry[1]

    return desc_table


def get_arp_info(session):
    crt = session['crt']

    arp_filename = ""
    arp_filename = crt.Dialog.FileOpenDialog(
        "Please select the ARP file to use when looking up MAC addresses.",
        "Open",
        arp_filename,
        "CSV Files (*.csv)|*.csv||")

    if arp_filename == "":
        return {}

    with open(arp_filename, 'r') as arp_file:
        arp_csv = csv.reader(arp_file)
        arp_list = [x for x in arp_csv]

    arp_lookup = {}
    # Process all ARP entries AFTER the header row.
    for entry in arp_list[1:]:
        # Get the IP address
        ip = entry[0]
        # Get the MAC address.  If 'Incomplete', skip entry
        mac = entry[2]
        if mac.lower() == 'incomplete':
            continue
        # Get the VLAN, if SVI is specified.
        intf = long_int_name(entry[3])
        if intf.lower().startswith('vlan'):
            vlan = intf[4:]
        else:
            vlan = None

        if intf in arp_lookup.keys():
            arp_lookup[intf].append((mac, ip))
        else:
            arp_lookup[intf] = [(mac, ip)]

        if mac in arp_lookup.keys():
            arp_lookup[mac].append((ip, vlan))
        else:
            arp_lookup[mac] = [(ip, vlan)]

    return arp_lookup


def main():
        # Run session start commands and save session information into a dictionary
        supported_os = ["IOS", "NX-OS"]
        session = start_session(crt, script_dir)

        # Make sure we completed session start.  If not, we'll receive None from start_session.
        if session:
            if session['OS'] not in supported_os:
                crt.Dialog.Messagebox("This device OS is not supported by this script.  Exiting.")
                return

            int_table = get_int_status(session)

            mac_table = get_mac_table(session)

            desc_table = get_desc_table(session)

            arp_lookup = get_arp_info(session)

            output = []
            for intf_entry in int_table:
                intf = intf_entry[0]
                # Exclude VLAN interfaces
                if intf.lower().startswith("v"):
                    continue

                state = intf_entry[2]
                # Get interface description, if one exists
                desc = None
                if intf in desc_table.keys():
                    desc = desc_table[intf]

                # Record upsteam information for routed ports
                if intf_entry[3] == 'routed':
                    vlan = intf_entry[3]
                    mac = None
                    ip = None
                    if intf in arp_lookup.keys():
                        arp_list = arp_lookup[intf]
                        for entry in arp_list:
                            mac, ip = entry
                            output_line = [intf, state, mac, ip, vlan, desc]
                            output.append(output_line)
                    else:
                        output_line = [intf, state, mac, ip, vlan, desc]
                        output.append(output_line)

                # Record all information for L2 ports
                elif intf in mac_table.keys():
                    for mac_entry in mac_table[intf]:
                        mac, vlan = mac_entry
                        ip = None
                        if mac and mac in arp_lookup.keys():
                            for entry in arp_lookup[mac]:
                                ip, arp_vlan = entry
                                if vlan == arp_vlan:
                                    output_line = [intf, state, mac, ip, vlan, desc]
                                    output.append(output_line)
                        else:
                            output_line = [intf, state, mac, ip, vlan, desc]
                            output.append(output_line)

                else:
                    output_line = [intf, state, None, None, None, desc]
                    output.append(output_line)

            output.sort(key=lambda x: human_sort_key(x[0]))
            output.insert(0, ["Interface", "Status", "MAC", "IP Address", "VLAN", "Description"])
            output_filename = create_output_filename(session, "PortMap", ext=".csv")
            list_of_lists_to_csv(session, output, output_filename,)

            # Clean up before closing session
            end_session(session)

if __name__ == "__builtin__":
    main()