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

from imports.google import textfsm


def get_template_full_path(session, filename):
    """
    This function generates the full filename to a TextFSM filename, which should exist in the
    "textfsm_templates" directory, which is in the same directory the script is run from.

    :param session:
    :param filename:
    :return:
    """
    script_dir = session["settings"]["script_dir"]
    return os.path.join(script_dir, "textfsm-templates", filename)


def textfsm_parse_to_list(input_data, template_filename, add_header=False):
    """
    Use TextFSM to parse the input text (from a command output) against the specified TextFSM template.   Use the
    default TextFSM output which is a list, with each entry of the list being a list with the values parsed.  Use
    add_header=True if the header row with value names should be prepended to the start of the list.
    
    :param input_data:  Path to the input file that TextFSM will parse.
    :param template_filename:  Path to the template file that will be used to parse the above data.
    :param add_header:  When True, will return a header row in the list.  This is useful for directly outputting to CSV. 
    :return: The TextFSM output (A list with each entry being a list of values parsed from the input)
    """

    # Create file object to the TextFSM template and create TextFSM object.
    with open(template_filename, 'r') as template:
        fsm_table = textfsm.TextFSM(template)

    # Process our raw data vs the template with TextFSM
    output = fsm_table.ParseText(input_data)

    # Insert a header row into the list, so that when output to a CSV there is a header row.
    if add_header:
        output.insert(0, fsm_table.header)

    return output


def textfsm_parse_to_dict(input_data, template_filename):
    """
    Use TextFSM to parse the input text (from a command output) against the specified TextFSM template.   Convert each
    list from the output to a dictionary, where each key in the TextFSM Value name from the template file.
    
    :param input_data:  Path to the input file that TextFSM will parse.
    :param template_filename:  Path to the template file that will be used to parse the above data.
    :return: A list, with each entry being a dictionary that maps TextFSM variable name to corresponding value.
    """

    # Create file object to the TextFSM template and create TextFSM object.
    with open(template_filename, 'r') as template:
        fsm_table = textfsm.TextFSM(template)

    # Process our raw data vs the template with TextFSM
    fsm_list = fsm_table.ParseText(input_data)

    # Insert a header row into the list, so that when output to a CSV there is a header row.
    header_list = fsm_table.header

    # Combine the header row with each entry in fsm_list to create a dictionary representation.  Add to output list.
    output = []
    for entry in fsm_list:
        dict_entry = dict(zip(header_list, entry))
        output.append(dict_entry)

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
        if route['protocol'] == 'connected':
            connected[route['network']] = route['interface']
        if route['protocol'] == 'static':
            statics[route['network']] = route['nexthop']
        if route['nexthop'] and not route['interface']:
            unknowns[route['nexthop']] = None

    for nexthop in unknowns:
        unknowns[nexthop] = recursive_lookup(nexthop)

    for route in route_table:
        if not route['interface']:
            if route['nexthop'] in unknowns:
                route['interface'] = unknowns[route['nexthop']]


def normalize_protocol(raw_protocol):
    if raw_protocol[0] == 'S' or "static" in raw_protocol:
        return 'static'
    elif raw_protocol[0] == 'C' or 'direct' in raw_protocol:
        return 'connected'
    elif raw_protocol[0] == 'L' or 'local' in raw_protocol:
        return 'local'
    elif raw_protocol[0] == 'D':
        return 'eigrp'
    elif raw_protocol[0] == 'O':
        return 'ospf'
    elif raw_protocol[0] == 'B':
        return 'bgp'
    elif raw_protocol[0] == 'i':
        return 'isis'
    elif raw_protocol[0] == 'R':
        return 'rip'
    else:
        return raw_protocol


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
        ('fastethernet', 'Fa'),
        ('ethernet', 'Eth'),
        ('port-channel', 'Po'),
        ('loopback', "Lo")
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
        ('Gi', 'GigabitEthernet'),
        ('F', 'FastEthernet'),
        ('Eth', 'Ethernet'),
        ('e', 'Ethernet'),
        ('Po', 'port-channel'),
        ('Lo', 'Loopback')
    ]
    for pair in replace_pairs:
        if pair[0] in int_name:
            return int_name.replace(pair[0], pair[1])
    else:
        return str


def extract_system_name(device_id, strip_list=[]):
    """
    In the CDP output some systems return a Hostname(Serial Number) format, while others return Serial(Hostname) output.
    This function tries to extract the system name from the CDP output and ignore the serial number.
    
    :param device_id: The device_id as learned from CDP.
    :param strip_list: A list of strings that should be removed from the hostname, if found
    :return: 
    """
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
            for item in strip_list:
                if item in system_name:
                    system_name = system_name.replace(item, '')
            return system_name
    else:
        return system_name
