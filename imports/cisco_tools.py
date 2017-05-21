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

from imports.google import ipaddress
from imports.google import textfsm


def parse_cdp_details(raw_cdp_output):

    # TextFSM template for parsing "show cdp neighbor detail" output
    cdp_template_path = "textfsm-templates/cdp-detail"

    # Create file object to the TextFSM template and create TextFSM object.
    with open(cdp_template_path, 'r') as template:
        cdp_table = textfsm.TextFSM(template)

    # Process our raw data vs the template with TextFSM
    output = cdp_table.ParseText(raw_cdp_output)

    # Insert a header row into the list, so that when output to a CSV there is a header row.
    output.insert(0, cdp_table.header)

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


def parse_ios_routes(routelist):
    """
    This function parses the raw IOS route table into a datastucture that can
    be used to more easily extract information.  The data structure that is
    returned in a list of dictionaries.  Each dictionary entry represents an
    entry in the route table and contains the following keys:

    {"protocol", "network", "AD", "metric", "nexthop", "lifetime", "interface"}

    """

    route_table = []
    # Various RegEx expressions to match varying parts of a route table line
    # I did it this way to break up the regex into more manageable parts,
    # Plus some of these parts can be found in mutliple line types
    # I'm also using named groups to more easily extract the needed data.
    #
    # Protocol (letter code identifying route entry)
    re_prot = r'(?P<protocol>\w[\* ][\w]{0,2})[ ]+'
    # Matches network address of route:  x.x.x.x/yy
    re_net = r'(?P<network>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d+)?)[ ]+'
    # Matches the Metric and AD: i.e. [110/203213]
    re_metric = r'\[(?P<ad>\d+)/(?P<metric>\d+)\][ ]+'
    # Matches the next hop in the route statement - "via y.y.y.y"
    re_nexthop = r'via (?P<nexthop>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}),?[ ]*'
    # Matches the lifetime of the route, usually in a format like 2m3d. Optional
    re_lifetime = r'(?P<lifetime>[\w:]+)?(, )?'
    # Matches outgoing interface. Not all protocols track this, so it is optional
    re_interface = r'(?P<interface>[\w-]+[\/\.\d]*)?'

    # Combining expressions above to build possible lines found in the route table
    #
    # Single line route entry
    re_single = re_prot + re_net + re_metric + re_nexthop + re_lifetime + re_interface
    # Directly connected route
    re_connected = re_prot + re_net + 'is directly connected, ' + re_interface
    # Subnetted routes, where the mask is only learned from the title line, such as
    # '2.0.0.0/24 is subnetted, 4 subnets'.   This is different from 'variably subnetted'
    # as the mask it given on every route that is variably subnetted.
    re_subnetted = r'[ ]*' + re_net + 'is subnetted,'
    # When the route length exceeds 80 chars, it is split across lines.  This is
    # the first line -- just the protocol and network.
    re_multiline = re_prot + re_net
    # This is the format seen for either a second ECMP path, or when the route has
    # been broken up across lines because of the length.
    re_ecmp = r'[ ]*' + re_metric + re_nexthop + re_lifetime + re_interface

    # Compile RegEx expressions
    reSingle = re.compile(re_single)
    reConnected = re.compile(re_connected)
    reSubnetted = re.compile(re_subnetted)
    reMultiline = re.compile(re_multiline)
    reECMP = re.compile(re_ecmp)

    # Start parsing raw route table into a data structure.  Each route entry goes
    # into a dict, and all the entries are collected into a list.
    for entry in routelist:
        route_entry = {}

        regex = reSubnetted.match(entry)
        if regex:
            supernet = ipaddress.ip_network(u'{}'.format(regex.group('network')))
            prev_mask = str(supernet.netmask)

        regex = reSingle.match(entry)
        if regex:
            # Need to track protocol and network in case the next line is a 2nd
            # equal cost path (which doesn't show that info)
            prev_prot = regex.group('protocol')
            net_string = regex.group('network')
            if "/" not in net_string:
                prev_net = ipaddress.ip_network(u'{}'.format(net_string + "/" + prev_mask))
            else:
                prev_net = ipaddress.ip_network(u'{}'.format(net_string))
            route_entry = {"protocol": prev_prot,
                           "network": prev_net,
                           "AD": regex.group('ad'),
                           "metric": regex.group('metric'),
                           "nexthop": ipaddress.ip_address(u'{}'.format(regex.group('nexthop'))),
                           "lifetime": regex.group('lifetime'),
                           "interface": regex.group('interface')
                          }
        else:
            regex = reConnected.match(entry)
            if regex:
                net_string = regex.group('network')
                if "/" not in net_string:
                    this_net = ipaddress.ip_network(u'{}'.format(net_string + "/" + prev_mask))
                else:
                    this_net = ipaddress.ip_network(u'{}'.format(net_string))
                route_entry = {"protocol": regex.group('protocol'),
                               "network": this_net,
                               "AD": 0,
                               "metric": 0,
                               "nexthop": None,
                               "interface": regex.group('interface')
                              }
            else:
                regex = reMultiline.match(entry)
                if regex:
                    # Since this is the first line in an entry that was broken
                    # up due to length, only record protocol and network.
                    # The next line has the rest of the data needed.
                    prev_prot = regex.group('protocol')
                    prev_net = ipaddress.ip_network(u'{}'.format(regex.group('network')))
                else:
                    regex = reECMP.match(entry)
                    if regex:
                        # Since this is a second equal cost entry, use
                        # protocol and network info from previous entry
                        route_entry = {"protocol": prev_prot,
                                       "network": prev_net,
                                       "AD": regex.group('ad'),
                                       "metric": regex.group('metric'),
                                       "nexthop": ipaddress.ip_address(u'{}'.format(regex.group('nexthop'))),
                                       "lifetime": regex.group('lifetime'),
                                       "interface": regex.group('interface')
                                      }
        if route_entry != {}:
            route_table.append(route_entry)
    update_empty_interfaces(route_table)
    return route_table


def parse_nxos_routes(routelist):
    """
    This function parses the raw NXOS route table into a datastucture that can
    be used to more easily extract information.  The data structure that is
    returned in a list of dictionaries.  Each dictionary entry represents an
    entry in the route table and contains the following keys:

    {"protocol", "network", "AD", "metric", "nexthop", "lifetime", "interface"}

    """

    routetable = []
    ignore_protocols = ["local", "hsrp"]
    # Various RegEx expressions to match varying parts of a route table line
    # I did it this way to break up the regex into more manageable parts,
    # Plus some of these parts can be found in mutliple line types
    # I'm also using named groups to more easily extract the needed data.
    #
    re_via = r'^[ ]+\*?via '
    # Matches network address of route:  x.x.x.x/yy
    re_net = r'(?P<network>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d+),\W+ubest\/mbest:'
    # Matches the next hop in the route statement - "via y.y.y.y"
    re_nexthop = r'(?P<nexthop>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}),'
    # Matches outgoing interface. Not all protocols track this, so it is optional
    re_interface = r'[ ]+(?P<interface>\w+\d+(\/\d+)?),'
    # Matches the Metric and AD: i.e. [110/203213]
    re_metric = r'[ ]+\[(?P<ad>\d+)\/(?P<metric>\d+)\],'
    # Matches the lifetime of the route, usually in a format like 2m3d. Optional
    re_lifetime = r'[ ]+(?P<lifetime>[\w:]+),'
    # Protocol (letter code identifying route entry)
    re_prot = r'[ ]+(?P<protocol>\w+(-\w+)?)[,]?'

    # Combining expressions above to build possible lines found in the route table
    # Standard via line from routing protocol
    re_nh_line = re_via + re_nexthop + re_interface + re_metric + re_lifetime + re_prot
    # Static routes don't have an outgoing interface.
    re_static = re_via + re_nexthop + re_metric + re_lifetime + re_prot

    # Compile RegEx expressions
    reNet = re.compile(re_net)
    reVia = re.compile(re_nh_line)
    reStatic = re.compile(re_static)

    # Start parsing raw route table into a data structure.  Each route entry goes
    # into a dict, and all the entries are collected into a list.
    for entry in routelist:
        routeentry = {}
        regex = reNet.match(entry)
        if regex:
            # Need to remember the network so the following next-hop lines
            # can be associated with the correct net in the dict.
            prev_net = ipaddress.ip_network(u'{}'.format(regex.group('network')))
        else:
            regex = reVia.match(entry)
            if regex:
                proto = regex.group('protocol')
                if proto in ignore_protocols:
                    pass
                elif proto == "direct":
                    routeentry = {"network": prev_net,
                                  "nexthop": None,
                                  "interface": regex.group('interface'),
                                  "AD": regex.group('ad'),
                                  "metric": regex.group('metric'),
                                  "lifetime": regex.group('lifetime'),
                                  "protocol": proto
                                  }
                else:
                    routeentry = {"network": prev_net,
                                  "nexthop": ipaddress.ip_address(u'{}'.format(regex.group('nexthop'))),
                                  "interface": regex.group('interface'),
                                  "AD": regex.group('ad'),
                                  "metric": regex.group('metric'),
                                  "lifetime": regex.group('lifetime'),
                                  "protocol": proto
                                  }
            else:
                regex = reStatic.match(entry)
                if regex:
                    routeentry = {"network": prev_net,
                                  "nexthop": ipaddress.ip_address(u'{}'.format(regex.group('nexthop'))),
                                  "interface": None,
                                  "AD": regex.group('ad'),
                                  "metric": regex.group('metric'),
                                  "lifetime": regex.group('lifetime'),
                                  "protocol": regex.group('protocol')
                                  }

        if routeentry != {}:
            routetable.append(routeentry)
    update_empty_interfaces(routetable)
    return routetable


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


def short_int(str):
    """
    This function shortens the interface name for easier reading
  
    :param str:  The input string (long interface name) 
    :return:  The shortened interface name
    """
    replace_pairs = [
        ('tengigabitethernet', 'T'),
        ('gigabitethernet', 'G'),
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


def short_name(name):
    """
    This function will remove any domain suffixes (.cisco.com) or serial numbers that show up in parenthesis after the 
    hostname of the CDP output

    :param name: 
    :return: 
    """
    # TODO: Some devices give IP address instead of name.  Need to ignore
    #       IP format.
    # TODO: Some CatOS devices put hostname in (), instead of serial number.
    #       Find a way to catch this when it happens.
    return name.split('.')[0].split('(')[0]
