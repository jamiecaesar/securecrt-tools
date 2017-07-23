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
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import list_of_lists_to_csv

from imports.cisco_tools import textfsm_parse_to_list

from imports.py_utils import human_sort_key


# #################################  SCRIPT  ###################################

def get_arp_info(session):
    crt = session['crt']

    arp_filename = ""
    arp_filename = crt.Dialog.FileOpenDialog(
        "Please select the ARP file to use when looking up MAC addresses.",
        "Open",
        arp_filename,
        "CSV Files (*.csv)|*.csv||")

    if arp_filename == "":
        return None

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
        intf = entry[4]
        if intf.startswith('Vlan'):
            vlan = intf[4:]
        else:
            vlan = None

        arp_lookup[mac] = (ip, vlan)

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

            send_cmd = "show mac address-table"
            raw_mac_list = get_output(session, send_cmd)

            # TextFSM template for parsing "show mac address-table" output
            if session['OS'] == "NX-OS":
                mac_template = "textfsm-templates/show-mac-addr-table-nxos"
            else:
                mac_template = "textfsm-templates/show-mac-addr-table-ios"

            template_path = os.path.join(script_dir, mac_template)

            mac_table = textfsm_parse_to_list(raw_mac_list, template_path, add_header=False)

            arp_lookup = get_arp_info(session)

            if arp_lookup:
                output = [["Interface", "MAC", "IP Address", "VLAN"]]
                for entry in mac_table:
                    mac = entry[0]
                    intf = entry[3]
                    ip = None
                    vlan = None
                    if mac in arp_lookup.keys():
                        lookup = arp_lookup[mac]
                        ip = lookup[0]
                        vlan = lookup[1]
                    output_line = [intf, mac, ip, vlan]
                    output.append(output_line)
                    output.sort(key=lambda x: human_sort_key(x[0]))
                output_filename = create_output_filename(session, "PortMap", ext=".csv")
                list_of_lists_to_csv(output, output_filename)

            # Clean up before closing session
            end_session(session)

if __name__ == "__builtin__":
    main()