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

from imports.cisco_tools import get_protocol
from imports.cisco_tools import parse_ios_routes
from imports.cisco_tools import parse_nxos_routes

from imports.py_utils import read_file_to_list
from imports.py_utils import list_of_lists_to_csv
from imports.py_utils import human_sort_key


# #################################  SCRIPT  ###################################


def nexthop_summary(route_list):
    """
    This function will take the routelist datastructure (created by ParseIOSRoutes) and process it into
    a datastructure containing the summary data, that is then converted to a list so it can be easily written
    into a CSV file (by list_to_csv).
     
    :param route_list: 
    :return: 
    """

    # There are 3 Dictionaries of information extracted from the route table:
    # 1) Summary information - List each next-hop with how many routes from each 
    #    protocol
    # 2) Connected Interfaces - List of the subnets that are on connected intfs
    # 3) Detailed information - List of each next-hop and all the networks that
    #    flow to that next-hop.
    summary_dict = {}
    connected_dict = {}
    detail_dict = {}

    for entry in route_list:
        # Verify this entry has a next-hop parameter
        if entry['nexthop']:
            nh = str(entry['nexthop'])
            proto = get_protocol(entry['protocol'])
            if nh in summary_dict:
                summary_dict[nh]['Total'] += 1
                summary_dict[nh][proto] += 1
            else:
                summary_dict[nh] = {'int': entry['interface'],
                                    'Total': 0,
                                    'Static': 0,
                                    'EIGRP': 0,
                                    'OSPF': 0,
                                    'BGP': 0,
                                    'ISIS': 0,
                                    'RIP': 0,
                                    'Other': 0
                                    }
                summary_dict[nh]['Total'] += 1
                summary_dict[nh][proto] += 1
            if nh in detail_dict:
                # Append the network and protocol (in a tuple)
                detail_dict[nh].append((str(entry['network']), proto))
            else:
                # Create an entry for the next-hop and add network/proto to list.
                detail_dict[nh] = [(str(entry['network']), proto)]
        elif entry['interface']:
            if entry['interface'] in connected_dict:
                connected_dict[entry['interface']].append(str(entry['network']))
            else:
                connected_dict[entry['interface']] = [str(entry['network'])]

    # Process Summary Data
    nexthops = [['Next-hop', 'Interface', 'Total routes', 'Static', 'EIGRP', 'OSPF', 'BGP', 'ISIS', 'RIP', 'Other']]
    # Put next-hop stats into list for writing into a CSV file
    nexthops_data = []
    for key, value in summary_dict.iteritems():
        nexthops_data.append([key, value['int'], value['Total'], value['Static'], value['EIGRP'],
                              value['OSPF'], value['BGP'], value['ISIS'], value['RIP'], value['Other']])

    # Append sorted nexthops stats after header line
    nexthops.extend(sorted(nexthops_data, key=lambda x: human_sort_key(x[0])))

    # Process Connected Network Data
    connected = [['', ''], ['', ''], ['Connected', ''], ['Interface', 'Network(s)']]
    conn_data = []
    for key, value in connected_dict.iteritems():
        this_row = [key]
        this_row.extend(value)
        conn_data.append(this_row)
    connected.extend(sorted(conn_data, key=lambda x: human_sort_key(x[0])))

    # Process Detailed Route Data
    detailed = [['', '', ''], ['', '', ''], ['Route Details', '', ''], ['Next-Hop', 'Network(s)', 'Protocol']]
    detail_data = []
    sorted_keys = sorted(detail_dict, key=lambda x: human_sort_key(x))
    for key in sorted_keys:
        new_list = sorted(detail_dict[key], key=lambda x: human_sort_key(x[0]))
        for entry in new_list:
            this_row = [key, entry[0], entry[1]]
            detail_data.append(this_row)
        detail_data.extend([''])
    detailed.extend(detail_data)

    return nexthops, connected, detailed


def main():
    supported_os = ["IOS", "IOS XE", "NX-OS"]
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
        routes = read_file_to_list(temp_routes_filename)
        os.remove(temp_routes_filename)

        if session['OS'] == "NX-OS":
            route_list = parse_nxos_routes(routes)
        else:
            route_list = parse_ios_routes(routes)
            
        # Get a list of all nexthop stats as well as connected networks (2 lists).
        nexthops, connected, detailed = nexthop_summary(route_list)
        
        # Merge the nexthops and connected interfaces into a single list before writing.
        nexthops.extend(connected)
        nexthops.extend(detailed)
        
        # Write data into a CSV file.
        output_filename = create_output_filename(session, "NextHopSummary", ext='.csv')
        list_of_lists_to_csv(nexthops, output_filename)
    else:
        error_str = "This script does not support {}.\n" \
                    "It will currently only run on IOS Devices.".format(session['OS'])
        crt.Dialog.MessageBox(error_str, "Unsupported Network OS", 16)

    # Clean up before exiting
    end_session(session)


if __name__ == "__builtin__":
    main()