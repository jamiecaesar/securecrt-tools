# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will grab the route table information from a Cisco IOS device and export some statistics to a CSV file.
# 
#

# ##############################  SCRIPT SETTING  ###############################
#
# Settings for this script are saved in the "script_settings.json" file that should be located in the same directory as
# this script.
#


# #################################  IMPORTS  ##################################
# Import OS and Sys module to be able to perform required operations for adding
# the script directory to the python path (for loading modules), and manipulating
# paths for saving files.
import os
import sys

# Add the script directory to the python path (if not there) so we can import 
# modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Imports from common SecureCRT library
from imports.cisco_securecrt import start_session
from imports.cisco_securecrt import end_session
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import write_output_to_file

from imports.cisco_tools import normalize_protocol
from imports.cisco_tools import textfsm_parse_to_dict
from imports.cisco_tools import update_empty_interfaces

from imports.py_utils import list_of_lists_to_csv
from imports.py_utils import human_sort_key

import imports.google.ipaddress as ipaddress

# #################################  SCRIPT  ###################################


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
        # If not a supported OS, return an empty list
        return []

    # Normalize path before attempting to access (e.g. change slash to backslash for windows.)
    template_file = os.path.normpath(template_file)
    route_table = textfsm_parse_to_dict(routes, template_file)

    complete_table = []
    for route in route_table:
        new_entry = {}

        new_entry['network'] = ipaddress.ip_network(u"{0}/{1}".format(route['NETWORK'], route['MASK']))

        new_entry['protocol'] = normalize_protocol(route['PROTOCOL'])

        if route['NEXTHOP_IP'] == '':
            new_entry['nexthop'] = None
        else:
            new_entry['nexthop'] = ipaddress.ip_address(unicode(route['NEXTHOP_IP']))

        if route["NEXTHOP_IF"] == '':
            new_entry['interface'] = None
        else:
            new_entry['interface'] = route['NEXTHOP_IF']

        # Nexthop VRF will only occur in NX-OS route tables (%vrf-name after the nexthop)
        if 'NEXTHOP_VRF' in route:
            if route['NEXTHOP_VRF'] == '':
                new_entry['vrf'] = None
            else:
                new_entry['vrf'] = route['NEXTHOP_VRF']

        complete_table.append(new_entry)

    update_empty_interfaces(complete_table)
    return complete_table


def nexthop_summary(textfsm_dict):
    # Identify connected or other local networks -- most found in NXOS to exlude from next-hops.  These are excluded
    # from the nexthop summary (except connected has its own section in the output).
    local_protos = ['connected', 'local', 'hsrp', 'vrrp', 'glbp']

    # Create a list of all dynamic protocols from the provided route table.  Add total and statics to the front.
    proto_list = []
    for entry in textfsm_dict:
        if entry['protocol'] not in proto_list and entry['protocol'] not in local_protos:
            proto_list.append(entry['protocol'])
    proto_list.sort(key=human_sort_key)
    proto_list.insert(0, 'total')
    proto_list.insert(0, 'interface')

    # Create dictionaries to store summary information as we process the route table.
    summary_table = {}
    connected_table = {}
    detailed_table = {}

    # Process the route table to populate the above 3 dictionaries.
    for entry in textfsm_dict:
        # If the route is connected, local or an FHRP entry
        if entry['protocol'] in local_protos:
            if entry['protocol'] == 'connected':
                if entry['interface'] not in connected_table:
                    connected_table[entry['interface']] = []
                connected_table[entry['interface']].append(str(entry['network']))
        else:
            if entry['nexthop']:
                if 'vrf' in entry and entry['vrf']:
                    nexthop = "{0}%{1}".format(entry['nexthop'], entry['vrf'])
                else:
                    nexthop = str(entry['nexthop'])
            elif entry['interface'].lower() == "null0":
                nexthop = 'discard'

            if nexthop not in summary_table:
                # Create an entry for this next-hop, containing zero count for all protocols.
                summary_table[nexthop] = {}
                summary_table[nexthop].update(zip(proto_list, [0] * len(proto_list)))
                summary_table[nexthop]['interface'] = entry['interface']
            # Increment total and protocol specific count
            summary_table[nexthop][entry['protocol']] += 1
            summary_table[nexthop]['total'] += 1

            if nexthop not in detailed_table:
                detailed_table[nexthop] = []
            detailed_table[nexthop].append((str(entry['network']), entry['protocol']))

    # Convert summary_table into a format that can be printed to the CSV file.
    output = []
    header = ["Nexthop", "Interface", "Total"]
    header.extend(proto_list[2:])
    output.append(header)
    summary_keys = sorted(summary_table.keys(), key=human_sort_key)
    for key in summary_keys:
        line = [key]
        for column in proto_list:
            line.append(summary_table[key][column])
        output.append(line)
    output.append([])

    # Convert the connected_table into a format that can be printed to the CSV file (and append to output)
    output.append([])
    output.append(["Connected:"])
    output.append(["Interface", "Network(s)"])
    connected_keys = sorted(connected_table.keys(), key=human_sort_key)
    for key in connected_keys:
        line = [key]
        for network in connected_table[key]:
            line.append(network)
        output.append(line)
    output.append([])

    # Convert the detailed_table into a format that can be printed to the CSV file (and append to output)
    output.append([])
    output.append(["Route Details"])
    output.append(["Nexthop", "Network", "Protocol"])
    detailed_keys = sorted(detailed_table.keys(), key=human_sort_key)
    for key in detailed_keys:
        for network in detailed_table[key]:
            line = [key]
            line.extend(list(network))
            output.append(line)
        output.append([])

    # Return the output, ready to be sent to directly to a CSV file
    return output



def main():
    supported_os = ["IOS", "NX-OS"]
    send_cmd = "show ip route"

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Get VRF that we are interested in
    selected_vrf = crt.Dialog.Prompt("Enter the VRF name.\n(Leave blank for default VRF)")
    if selected_vrf != "":
        send_cmd = send_cmd + " vrf {0}".format(selected_vrf)
        session['hostname'] = session['hostname'] + "-VRF-{0}".format(selected_vrf)
    
    # Generate filename used for output files.
    temp_routes_filename = create_output_filename(session, "NextHopSummary")

    if session['OS'] in supported_os:
        # Dumping directly to a huge string has problems when the route table is large (1000+ lines)
        # Save raw "show ip route" output to a file, read it back in as a list of strings and delete temp file.
        write_output_to_file(session, send_cmd, temp_routes_filename)
        with open(temp_routes_filename, 'r') as route_file:
            routes = route_file.read()
        os.remove(temp_routes_filename)

        route_list = parse_routes(session, routes)

        output_filename = create_output_filename(session, "NextHopSummary", ext='.csv')

        # Process TextFSM output into list of lists (for direct output to CSV)
        output_data = nexthop_summary(route_list)
        # Write data into a CSV file.
        list_of_lists_to_csv(output_data, output_filename)
    else:
        error_str = "This script does not support {}.\n" \
                    "It will currently only run on IOS Devices.".format(session['OS'])
        crt.Dialog.MessageBox(error_str, "Unsupported Network OS", 16)

    # Clean up before exiting
    end_session(session)


if __name__ == "__builtin__":
    main()