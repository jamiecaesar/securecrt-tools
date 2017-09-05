# $language = "python"
# $interface = "1.0"

# ################################################   SCRIPT INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# This script will first prompt for the location of the ARP table to use for processing.   Next, the mac address table
# of the active session will be captured and a CSV file showing the MAC address and IP of what is attached to each port
# on the device will be output.
#


# ################################################  SCRIPT SETTING  ###################################################
#
# Global settings that affect all scripts (output directory, date format, etc) is stored in the "global_settings.json"
# file in the "settings" directory.
#
# If any local settings are used for this script, they will be stored in the same settings folder, with the same name
# as the script that uses them, except ending with ".json".
#
# All settings can be manually modified in JSON format (the same syntax as Python lists and dictionaries). Be aware of
# required commas between items, or else options are likely to get run together and break the script.
#
# **IMPORTANT**  All paths saved in .json files must contain either forward slashes (/home/jcaesar) or
# DOUBLE back-slashes (C:\\Users\\Jamie).   Single backslashes will be considered part of a control character and will
# cause an error on loading.
#


# ################################################     IMPORTS      ###################################################
import os
import sys
import csv
import logging

# If the "crt" object exists, this is being run from SecureCRT.  Get script directory so we can add it to the
# PYTHONPATH, which is needed to import our custom modules.
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))
os.chdir(script_dir)

# Now we can import our custom modules
import securecrt_tools.sessions as sessions
import securecrt_tools.settings as settings
import securecrt_tools.utilities as utils


# ################################################  LOAD SETTINGS   ###################################################

session_set_filename = os.path.join(script_dir, "settings", settings.global_settings_filename)
session_settings = settings.SettingsImporter(session_set_filename, settings.global_defs)

# Set logger variable -- this won't be used unless debug setting is True
logger = logging.getLogger("securecrt")

# ################################################     SCRIPT       ###################################################

def get_int_status(session):
    send_cmd = "show interface status"

    if session.os == "IOS":
        int_template = "textfsm-templates/cisco_ios_show_interfaces_status.template"
    else:
        int_template = "textfsm-templates/cisco_nxos_show_interface_status.template"

    raw_int_status = session.get_command_output(send_cmd)
    fsm_results = utils.textfsm_parse_to_list(raw_int_status, int_template)

    for entry in fsm_results:
        entry[0] = utils.long_int_name(entry[0])

    return fsm_results


def get_mac_table(session):
    send_cmd = "show mac address-table"
    peer_link = None   # Defining variable to hold peer link information if we have an NXOS output

    # TextFSM template for parsing "show mac address-table" output
    if session.os == "IOS":
        template_file = "textfsm-templates/cisco_ios_show_mac_addr_table.template"
    else:
        template_file = "textfsm-templates/cisco_nxos_show_mac_addr_table.template"

    logger.debug("Using template: '{0}'".format(template_file))

    raw_mac = session.get_command_output(send_cmd)
    mac_table = utils.textfsm_parse_to_list(raw_mac, template_file, add_header=True)

    # Check if IOS mac_table is empty -- if so, it is probably because the switch has an older IOS
    # that expects "show mac-address-table" instead of "show mac address-table".
    if session.os == "IOS" and len(mac_table) == 1:
        send_cmd = "show mac-address-table dynamic"
        logger.debug("Retrying with command set to '{0}'".format(send_cmd))

        raw_mac = session.get_command_output(send_cmd)

        mac_table = utils.textfsm_parse_to_list(raw_mac, template_file, add_header=True)

    # Check for vPCs on NXOS to account for "vPC Peer-Link" entries in MAC table of N9Ks
    elif session.os == "NXOS":
        send_cmd = "show vpc"
        vpc_template = "textfsm-templates/cisco_nxos_show_vpc.template"

        raw_show_vpc = session.get_command_output(send_cmd)
        vpc_table = utils.textfsm_parse_to_list(raw_show_vpc, vpc_template)

        if len(vpc_table) > 0:
            peer_link_record = vpc_table[0]
            peer_link = utils.long_int_name(peer_link_record[1])
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
            intf = utils.long_int_name(raw_intf)

        if intf in output:
            output[intf].append((mac, vlan))
        else:
            output[intf] = [(mac, vlan)]

    return output


def get_desc_table(session):
    send_cmd = "show interface description"

    if session.os == "IOS":
        int_template = "textfsm-templates/cisco_ios_show_interfaces_description.template"
    else:
        int_template = "textfsm-templates/cisco_nxos_show_interface_description.template"

    raw_int_desc = session.get_command_output(send_cmd)
    desc_list = utils.textfsm_parse_to_list(raw_int_desc, int_template)

    desc_table = {}
    # Change interface names to long versions for better matching with other outputs
    for entry in desc_list:
        intf = utils.long_int_name(entry[0])
        desc_table[intf] = entry[1]

    return desc_table


def get_arp_info(session):
    arp_filename = session.file_open_dialog("Please select the ARP file to use when looking up MAC addresses.",
                                            "Open", "CSV Files (*.csv)|*.csv||")
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
        intf = utils.long_int_name(entry[3])
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


def script_main(session):
    supported_os = ["IOS", "NXOS"]
    if session.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Exiting program.".format(session.os))
        session.message_box("{0} is not a supported OS for this script.".format(session.os), "Unsupported OS",
                            options=sessions.ICON_STOP)
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

    output.sort(key=lambda x: utils.human_sort_key(x[0]))
    output.insert(0, ["Interface", "Status", "MAC", "IP Address", "VLAN", "Description"])
    output_filename = session.create_output_filename("PortMap", ext=".csv")
    utils.list_of_lists_to_csv(output, output_filename)

    # Clean up before closing session
    session.end()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, create our session object using the "crt" object provided by SecureCRT
if __name__ == "__builtin__":
    # Create a session object for this execution of the script and pass it to our main() function
    crt_session = sessions.CRTSession(crt, session_settings)
    script_main(crt_session)

# Else, if this script is run directly then create a session object without the SecureCRT API (crt object)  This would
# be done for debugging purposes (running the script outside of SecureCRT and feeding it the output it failed on)
elif __name__ == "__main__":
    direct_session = sessions.DirectSession(os.path.realpath(__file__), session_settings)
    script_main(direct_session)