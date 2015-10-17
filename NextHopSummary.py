# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script will grab the route table information from a Cisco IOS device 
# and export some statistics to a CSV file.
# 
# The path where the file is saved is specified in the "save_path" variable in
# the settings section below.

###############################  SCRIPT SETTING  ###############################
#
# Settings for this script are saved in the "script_settings.py" file that
# should be located in the same directory as this script.
#


##################################  IMPORTS  ##################################
# Import OS and Sys module to be able to perform required operations for adding
# the script directory to the python path (for loading modules), and manipulating
# paths for saving files.
import os
import sys
import re

# Add the script directory to the python path (if not there) so we can import 
# modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import Settings from Settings File
from script_settings import settings

# Imports from common SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import DetectNetworkOS
from ciscolib import GetFilename
from ciscolib import WriteOutput
from ciscolib import ReadFileToList
from ciscolib import ParseIOSRoutes
from ciscolib import ParseNXOSRoutes
from ciscolib import alphanum_key
from ciscolib import ListToCSV

##################################  SCRIPT  ###################################

def NextHopSummary(routelist):
    '''
    This function will take the routelist datastructure (created by ParseIOSRoutes) and process it into
    a datastructure containing the summary data, that is then converted to a list so it can be easily written
    into a CSV file (by ListToCSV).
    '''
    def GetProtocol(raw_protocol):
        if raw_protocol[0] == 'S' or "static" in raw_protocol:
            return 'Static'
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

    summaryDict = {}
    connectedDict = {}
    for entry in routelist:
        # Verify this entry has a next-hop parameter
        if entry['nexthop']:
            nh = entry['nexthop']
            proto = GetProtocol(entry['protocol'])
            intf = entry['interface']
            if nh in summaryDict:
                summaryDict[nh]['Total'] += 1
                summaryDict[nh][proto] += 1
            else:
                summaryDict[entry['nexthop']] = { 'int' : entry['interface'],
                                                  'Total': 0, 
                                                  'Static': 0, 
                                                  'EIGRP': 0, 
                                                  'OSPF' : 0, 
                                                  'BGP':0, 
                                                  'ISIS': 0, 
                                                  'RIP' : 0, 
                                                  'Other' : 0 
                                                  }
                summaryDict[nh]['Total'] += 1
                summaryDict[nh][proto] += 1
        elif entry['interface']:
            if entry['interface'] in connectedDict:
                connectedDict[entry['interface']].append(entry['network'])
            else:
                connectedDict[entry['interface']] = [ entry['network'] ]

    nexthops = [['Next-hop', 'Interface', 'Total routes', 'Static', 'EIGRP', 'OSPF', 'BGP', 'ISIS', 'RIP', 'Other']]
    # Put next-hop stats into list for writing into a CSV file
    nexthops_data = []
    for key, value in summaryDict.iteritems():
        nexthops_data.append([key, value['int'], value['Total'], value['Static'], value['EIGRP'], 
                         value['OSPF'], value['BGP'], value['ISIS'], value['RIP'], value['Other']])
    # Append sorted nexthops stats after header line
    nexthops.extend(sorted(nexthops_data, key=lambda x: alphanum_key(x[0])))

    connected = [ ['',''],
                  ['Connected', ''],
                  ['Interface', 'Network(s)']]
    conn_data = []
    for key, value in connectedDict.iteritems():
        this_row = [ key ]
        this_row.extend(value)
        conn_data.append(this_row)
    connected.extend(sorted(conn_data, key=lambda x: alphanum_key(x[0])))
    return nexthops, connected


def Main():
    SupportedOS = ["IOS", "IOS XE", "NX-OS"]
    SendCmd = "show ip route"

    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)

    # Get VRF that we are interested in
    selected_vrf = crt.Dialog.Prompt("Enter the VRF name.\n(Leave blank for default VRF)")
    if selected_vrf != "":
        SendCmd = SendCmd + " vrf {0}".format(selected_vrf)
        session['hostname'] = session['hostname'] + "-VRF-{0}".format(selected_vrf)
    
    # Generate filename used for output files.
    fullFileName = GetFilename(session, settings, "NextHopSummary")

    if session['OS'] in SupportedOS:
        # Save raw "show ip route" output to a file.  Dumping directly to a huge 
        # string has problems when the route table is large (1000+ lines)
        WriteOutput(session, SendCmd, fullFileName)

        routes = ReadFileToList(fullFileName)
        if session['OS'] == "NX-OS":
            routelist = ParseNXOSRoutes(routes)
        else:
            routelist = ParseIOSRoutes(routes)

        # If the settings allow it, delete the temporary file that holds show cmd output
        if settings['delete_temp']:    
            os.remove(fullFileName + ".txt")
            
        # Get a list of all nexthop stats as well as connected networks (2 lists).
        nexthops, connected = NextHopSummary(routelist)
        
        # Merge the nexthops and connected interfaces into a single list before writing.
        nexthops.extend(connected)
        
        # Write data into a CSV file.
        ListToCSV(nexthops, fullFileName)
    else:
        error_str = "This script does not support {}.\n" \
                    "It will currently only run on IOS Devices.".format(session['OS'])
        crt.Dialog.MessageBox(error_str, "Unsupported Network OS", 16)

    # Clean up before exiting
    EndSession(session)


if __name__ == "__builtin__":
    Main()