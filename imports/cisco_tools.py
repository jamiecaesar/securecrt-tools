# ###############################  MODULE  INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
#    !!!! NOTE:  THIS IS NOT A SCRIPT THAT CAN BE RUN IN SECURECRT. !!!!
#
# This is a Python module that contains commonly used functions for processing the output of Cisco show commands.
# These functions do not require the session data to interact with SecureCRT sessions.
#
#

# #################################  IMPORTS   ##################################
import re
import os

from imports.google import ipaddress
from imports.google import textfsm


def parse_with_textfsm(raw_output, template_path, add_header=True):

    # Create file object to the TextFSM template and create TextFSM object.
    with open(template_path, 'r') as template:
        fsm_table = textfsm.TextFSM(template)

    # Process our raw data vs the template with TextFSM
    output = fsm_table.ParseText(raw_output)

    # Insert a header row into the list, so that when output to a CSV there is a header row.
    if add_header:
        output.insert(0, fsm_table.header)

    return output


def update_empty_interfaces(route_table):

    def recursive_lookup(nexthop):
        for network in connected:
            if nexthop in network:
                return connected[network]
        for network in statics:
            if nexthop in network:
                return recursive_lookup(statics[network])
        return None

    connected = {}
    unknowns = {}
    statics = {}
    for route in route_table:
        if route['protocol'][0] == 'C' or 'direct' in route['protocol']:
            connected[route['network']] = route['interface']
        if route['protocol'][0] == 'S' or 'static' in route['protocol']:
            statics[route['network']] = route['nexthop']
        if route['nexthop'] and not route['interface']:
            unknowns[route['nexthop']] = None

    for nexthop in unknowns:
        unknowns[nexthop] = recursive_lookup(nexthop)

    for route in route_table:
        if not route['interface']:
            if route['nexthop'] in unknowns:
                route['interface'] = unknowns[route['nexthop']]


def parse_routes(session, routes):
    """
    This function will take the raw route table from a devices (and a supported OS), process it with TextFSM, which
    will return a list of lists.   Each sub-list in the TextFSM output represents a route entry.  Each of these entries
    will be converted into a dictionary so that each item can be referenced by name (used in nexthop_summary)
    :param session: Sessions data structure
    :param routes: raw 'show ip route' output
    :return: A list of dictionaries, with each dict representing a route.
    """
    script_dir = session['settings']['script_dir']
    if session['OS'] == "IOS":
        template_file = os.path.join(script_dir, "textfsm-templates/show-ip-route-ios")
    elif session['OS'] == "NX-OS":
        template_file = os.path.join(script_dir, "textfsm-templates/show-ip-route-nxos")
    else:
        return []

    route_list = parse_with_textfsm(routes, template_file, add_header=False)

    route_table = []
    for route in route_list:
        nexthop = route[6]
        if nexthop != '':
            print nexthop
            nexthop = ipaddress.ip_address(unicode(route[6]))
        else:
            nexthop = None
        route_entry = {"protocol": route[0],
                       "network": ipaddress.ip_network(u"{}{}".format(route[2], route[3])),
                       "AD": route[4],
                       "metric": route[5],
                       "nexthop": nexthop,
                       "lifetime": route[8],
                       "interface": route[7]
                       }
        route_table.append(route_entry)

    update_empty_interfaces(route_table)
    return route_table


def get_protocol(raw_protocol):
    if raw_protocol[0] == 'S' or "static" in raw_protocol:
        return 'Static'
    elif raw_protocol[0] == 'C' or 'direct' in raw_protocol:
        return 'Connected'
    elif raw_protocol[0] == 'D' or "eigrp" in raw_protocol:
        return 'EIGRP'
    elif raw_protocol[0] == 'O' or "ospf" in raw_protocol:
        return 'OSPF'
    elif raw_protocol[0] == 'B' or "bgp" in raw_protocol:
        return 'BGP'
    elif raw_protocol[0] == 'i' or "isis" in raw_protocol:
        return 'ISIS'
    elif raw_protocol[0] == 'R' or "rip" in raw_protocol:
        return 'RIP'
    else:
        return 'Other'


def short_int_name(str):
    """
    This function shortens the interface name for easier reading
  
    :param str:  The input string (long interface name) 
    :return:  The shortened interface name
    """
    replace_pairs = [
        ('fortygigabitethernet', 'Fo'),
        ('tengigabitethernet', 'Te'),
        ('gigabitethernet', 'Gi'),
        ('fastethernet', 'F'),
        ('ethernet', 'e'),
        ('eth', 'e'),
        ('port-channel', 'Po')
    ]
    lower_str = str.lower()
    for pair in replace_pairs:
        if pair[0] in lower_str:
            return lower_str.replace(pair[0], pair[1])
    else:
        return str


def long_int_name(int_name):
    """
    This function expands a short interface name to the full name

    :param str:  The input string (short interface name) 
    :return:  The shortened interface name
    """
    replace_pairs = [
        ('Fo', 'FortyGigabitEthernet'),
        ('Te', 'TenGigabitEthernet'),
        ('Gi', 'gigabitethernet'),
        ('F', 'FastEthernet'),
        ('Eth', 'Ethernet'),
        ('e', 'Ethernet'),
        ('Po', 'port-channel')
    ]
    for pair in replace_pairs:
        if pair[0] in int_name:
            return int_name.replace(pair[0], pair[1])
    else:
        return str


def extract_system_name(device_id):
    cisco_serial_format = r'[A-Z]{3}[A-Z0-9]{8}'
    ip_format = r'\d{1-3}\.\d{1-3}\.\d{1-3}\.\d{1-3}'
    re_serial = re.compile(cisco_serial_format)
    re_ip = re.compile(ip_format)

    # If we find an open paren, then we either have "SYSTEM_NAME(SERIAL)" or "SERIAL(SYSTEM-NAME)" format.  The latter
    # format is often seen in older devices.  Determine which is the system_name by matching regex for a Cisco serial.
    if "(" in device_id:
        left, right = device_id.split('(')
        right = right.strip(')')
        left_serial = re_serial.match(left)
        right_serial = re_serial.match(right)
        if right_serial:
            system_name = left
        elif left_serial:
            system_name = right
        else:
            system_name = device_id
    else:
        system_name = device_id

    # If FQDN, only take the host portion, otherwise return what we have.
    if "." in system_name:
        is_ip = re_ip.match(system_name)
        # Some device return IP as device_id.  In those cases, just return IP -- don't treat it like FQDN
        if is_ip:
            return system_name
        else:
            return system_name.split('.')[0]
    else:
        return system_name
