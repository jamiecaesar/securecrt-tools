# $language = "python"
# $interface = "1.0"

import os
import sys
import logging
import csv

# Add script directory to the PYTHONPATH so we can import our modules (only if run from SecureCRT)
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))

# Now we can import our custom modules
from securecrt_tools import scripts
from securecrt_tools import utilities

# Try importing the socket module for DNS lookups
try:
    import socket
except ImportError:
    pass

if socket:
    dns_lookup = True
else:
    dns_lookup = False

# Import the manuf module for MAC to Vendor lookups
import securecrt_tools.manuf as manuf

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(session, gateway_hostname=""):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will first prompt for the location of the ARP table to use for processing.   Next, the mac address table
    of the active session will be captured and a CSV file showing the MAC address and IP of what is attached to each port
    on the device will be output.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    # Validate device is running a supported OS
    session.validate_os(["IOS", "NXOS"])

    # Get additional information we'll need
    int_table = get_int_status(session)

    mac_table = get_mac_table(session)

    desc_table = get_desc_table(session)

    arp_lookup = get_arp_info(script)

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
            fqdn = None
            mac_vendor = None
            if intf in arp_lookup.keys():
                arp_list = arp_lookup[intf]
                for entry in arp_list:
                    mac, ip = entry
                    if mac:
                        mac_vendor = mac_to_vendor(mac)
                    if dns_lookup and ip:
                        try:
                            fqdn, _, _, = socket.gethostbyaddr(ip)
                        except socket.herror:
                            pass
                    output_line = [intf, state, mac, mac_vendor, fqdn, ip, vlan, desc]
                    output.append(output_line)
            else:
                output_line = [intf, state, mac, mac_vendor, fqdn, ip, vlan, desc]
                output.append(output_line)

        # Record all information for L2 ports
        elif intf in mac_table.keys():
            for mac_entry in mac_table[intf]:
                mac, vlan = mac_entry
                ip = None
                fqdn = None
                mac_vendor = None
                if mac and mac in arp_lookup.keys():
                    for entry in arp_lookup[mac]:
                        ip, arp_vlan = entry
                        if vlan == arp_vlan:
                            if mac:
                                mac_vendor = mac_to_vendor(mac)
                            if dns_lookup and ip:
                                try:
                                    fqdn, _, _, = socket.gethostbyaddr(ip)
                                except socket.herror:
                                    pass
                            output_line = [intf, state, mac, mac_vendor, fqdn, ip, vlan, desc]
                            output.append(output_line)
                else:
                    output_line = [intf, state, mac, mac_vendor, fqdn, ip, vlan, desc]
                    output.append(output_line)

        else:
            output_line = [intf, state, None, None, None, None, None, desc]
            output.append(output_line)

    output.sort(key=lambda x: utilities.human_sort_key(x[0]))
    output.insert(0, ["Interface", "Status", "MAC", "MAC Vendor", "DNS Name", "IP Address", "VLAN", "Description"])
    output_filename = session.create_output_filename("PortMap", ext=".csv")
    utilities.list_of_lists_to_csv(output, output_filename)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


def get_int_status(session):
    """
    A function that captures the "show interface status" command and returns the processed output from TextFSM

    :param session: The script object that represents this script being executed
    :type session: sessions.Session

    :return: TextFSM output from processing the "show interface status" command
    :rtype: list of list
    """
    if session.os == "IOS":
        template_file = session.script.get_template("cisco_ios_show_interfaces_status.template")
    else:
        template_file = session.script.get_template("cisco_nxos_show_interface_status.template")

    raw_int_status = session.get_command_output("show interface status")
    fsm_results = utilities.textfsm_parse_to_list(raw_int_status, template_file)

    for entry in fsm_results:
        entry[0] = utilities.long_int_name(entry[0])

    return fsm_results


def get_mac_table(session):
    """
    A function that captures the mac address table and returns an output dictionary that can be used to look up the MAC
    address and VLAN associated with an interface.

    :param session: The script object that represents this script being executed
    :type session: session.Session

    :return: A dictionary that allows lookups of MAC and VLAN information for interfaces
    :rtype: dict
    """
    send_cmd = "show mac address-table"
    peer_link = None   # Defining variable to hold peer link information if we have an NXOS output

    # TextFSM template for parsing "show mac address-table" output
    if session.os == "IOS":
        template_file = session.script.get_template("cisco_ios_show_mac_addr_table.template")
    else:
        template_file = session.script.get_template("cisco_nxos_show_mac_addr_table.template")\

    raw_mac = session.get_command_output(send_cmd)
    mac_table = utilities.textfsm_parse_to_list(raw_mac, template_file, add_header=True)

    # Check if IOS mac_table is empty -- if so, it is probably because the switch has an older IOS
    # that expects "show mac-address-table" instead of "show mac address-table".
    if session.os == "IOS" and len(mac_table) == 1:
        send_cmd = "show mac-address-table dynamic"
        logger.debug("Retrying with command set to '{0}'".format(send_cmd))

        raw_mac = session.get_command_output(send_cmd)

        mac_table = utilities.textfsm_parse_to_list(raw_mac, template_file, add_header=True)

    # Check for vPCs on NXOS to account for "vPC Peer-Link" entries in MAC table of N9Ks
    elif session.os == "NXOS":
        send_cmd = "show vpc"
        vpc_template = session.get_template("cisco_nxos_show_vpc.template")

        raw_show_vpc = session.get_command_output(send_cmd)
        vpc_table = utilities.textfsm_parse_to_list(raw_show_vpc, vpc_template)

        if len(vpc_table) > 0:
            peer_link_record = vpc_table[0]
            peer_link = utilities.long_int_name(peer_link_record[1])
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
            intf = utilities.long_int_name(raw_intf)

        if intf in output:
            output[intf].append((mac, vlan))
        else:
            output[intf] = [(mac, vlan)]

    return output


def get_desc_table(session):
    """
    A function that creates a lookup dictionary that can be used to get the description of an interface.

    :param session: The script object that represents this script being executed
    :type session: sessions.Session

    :return: A dictionary that allows getting the description of an interface by using the interface as the key.
    :rtype: dict
    """
    send_cmd = "show interface description"

    if session.os == "IOS":
        int_template = session.script.get_template("cisco_ios_show_interfaces_description.template")
    else:
        int_template = session.script.get_template("cisco_nxos_show_interface_description.template")

    raw_int_desc = session.get_command_output(send_cmd)
    desc_list = utilities.textfsm_parse_to_list(raw_int_desc, int_template)

    desc_table = {}
    # Change interface names to long versions for better matching with other outputs
    for entry in desc_list:
        intf = utilities.long_int_name(entry[0])
        desc_table[intf] = entry[1]

    return desc_table


def get_arp_info(script):
    """
    A function that reads in the "show ip arp" CSV file that should be taken from the default gateway device for the
    switch being port mapped, so we can fill in the correct IP addresses for each device.

    :param script: The script object that represents this script being executed
    :type script: scripts.Script

    :return: A dictionary that can be used to lookup both the MAC and IP associated with an interface, or the IP and
        VLAN associated with a MAC address.
    :rtype: dict
    """

    arp_filename = script.file_open_dialog("Please select the ARP file to use when looking up MAC addresses.", "Open",
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
        intf = utilities.long_int_name(entry[3])
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


def mac_to_vendor(mac):
    """Lookup MAC Vendor Info

    :param mac: MAC address to Lookup Vendor Info on
    :return: MAC Vendor
    """
    p = manuf.MacParser(script_dir + "/securecrt_tools/manuf")
    mac_manuf, mac_comment = p.get_all(mac)
    if mac_comment:
        return mac_comment
    else:
        return mac_manuf


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Get session object for the SecureCRT tab that the script was launched from.
    crt_session = crt_script.get_main_session()
    # Run script's main logic against our session
    script_main(crt_session)
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DirectScript(os.path.realpath(__file__))
    # Get a simulated session object to pass into the script.
    sim_session = direct_script.get_main_session()
    # Run script's main logic against our session
    script_main(sim_session)
    # Shutdown logging after
    logging.shutdown()
