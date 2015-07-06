# $language = "python"
# $interface = "1.0"

# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script will grab the route table information from a Cisco IOS device 
# and export some statistics to a CSV file.
# 
# The path where the file is saved is specified in the "savepath" variable in
# the Main() function.

import os
import datetime
import csv
import re
import sys

savepath = 'Dropbox/SecureCRT/Backups/'
mydatestr = '%Y-%m-%d-%H-%M-%S'

def GetHostname(tab):
    '''
    This function will capture the prompt of the device.  The script will capture the
    text that is sent back from the remote device, which includes what we typed being
    echoed back to us, so we have to account for that while we parse data.
    '''
    #Send two line feeds
    tab.Send("\n\n")
    
    # Waits for first linefeed to be echoed back to us
    tab.WaitForString("\n") 
    
    # Read the text up to the next linefeed.
    prompt = tab.ReadString("\n") 

    #Remove any trailing control characters
    prompt = prompt.strip()

    # Check for non-enable mode (prompt ends with ">" instead of "#")
    if prompt[-1] == ">": 
        return None

    # Get out of config mode if that is the active mode when the script was launched
    elif "(conf" in prompt:
        tab.Send("end\n")
        hostname = prompt.split("(")[0]
        tab.WaitForString(hostname + "#")
        # Return the hostname (everything before the first "(")
        return hostname
        
    # Else, Return the hostname (all of the prompt except the last character)        
    else:
        return prompt[:-1]


def short_int(str):
  ''' 
  This function shortens the interface name for easier reading 
  '''
  replace_pairs = [
  ('tengigabitethernet', 'T'),
  ('gigabitethernet', 'G'),
  ('fastethernet', 'F'),
  ('ethernet', 'e'),
  ('eth', 'e'),
  ('port-channel' , 'Po')
  ]
  lower_str = str.lower()
  for pair in replace_pairs:
    if pair[0] in lower_str:
        return lower_str.replace(pair[0], pair[1])
  else:
    return str


def WriteOutput(command, filename, prompt, tab):
    '''
    This function captures the raw output of the command supplied and returns it.
    The prompt variable is used to signal the end of the command output, and 
    the "tab" variable is object that specifies which tab the commands are 
    written to. 
    '''
    endings=["\r\n", prompt]
    newfile = open(filename, 'wb')

    # Send term length command and wait for prompt to return
    tab.Send('term length 0\n')
    tab.WaitForString(prompt)
    
    # Send command
    tab.Send(command + "\n")

    # Ignore the echo of the command we typed (including linefeed)
    tab.WaitForString(command.strip())

    # Loop to capture every line of the command.  If we get CRLF (first entry
    # in our "endings" list), then write that line to the file.  If we get
    # our prompt back (which won't have CRLF), break the loop b/c we found the
    # end of the output.
    while True:
        nextline = tab.ReadString(endings)
        # If the match was the 1st index in the endings list -> \r\n
        if tab.MatchIndex == 1:
            # For Nexus will have extra "\r"s in it, leading to extra lines at the
            # start of the file.  Don't write those.
            if nextline != "\r":
                # Write the line of text to the file
                # crt.Dialog.MessageBox("Original:" + repr(nextline) + "\nStripped:" + repr(nextline.strip('\r')))
                newfile.write(nextline.strip("\r") + "\r\n")
        else:
            # We got our prompt (MatchIndex is 2), so break the loop
            break
    
    newfile.close()
    
    # Send term length back to default
    tab.Send('term length 24\n')
    tab.WaitForString(prompt)


def ParseRawRoutes(routelist):
    '''
    This function parses the raw route table into a datastucture that can be used to more easily
    extract information.  The data structure that is returned in a list of dictionaries.
    Each dictionary entry represents an entry in the route table and contains the following keys:
    {"protocol", "network", "AD", "metric", "nexthop", "lifetime", "interface"}
    '''
    routetable = []
    # Various RegEx expressions to match varying parts of a route table line
    # I did it this way to break up the regex into more manageable parts, 
    # Plus some of these parts can be found in mutliple line types
    # I'm also using named groups to more easily extract the needed data.
    #
    # Protocol (letter code identifying route entry)
    re_prot= r'(?P<protocol>\w[\* ][\w]{0,2})[ ]+'
    # Matches network address of route:  x.x.x.x/yy
    re_net = r'(?P<network>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d+)?)[ ]+'
    # Matches the Metric and AD: i.e. [110/203213]
    re_metric = r'\[(?P<ad>\d+)/(?P<metric>\d+)\][ ]+'
    # Matches the next hop in the route statement - "via y.y.y.y"
    re_nexthop = r'via (?P<nexthop>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}),?[ ]*'
    # Matches the lifetime of the route, usually in a format like 2m3d. Optional
    re_lifetime = r'(?P<lifetime>\w+)?(, )?'
    # Matches outgoing interface. Not all protocols track this, so it is optional
    re_interface = r'(?P<interface>[\w-]+(/\d*)*)?'

    # Combining expressions above to build possible lines found in the route table
    #
    # Single line route entry
    re_single = re_prot + re_net + re_metric + re_nexthop + re_lifetime + re_interface
    # Directly connected route
    re_connected = re_prot + re_net + 'is directly connected, ' + re_interface
    # When the route length exceeds 80 chars, it is split across lines.  This is
    # the first line -- just the protocol and network.
    re_multiline = re_prot + re_net
    # This is the format seen for either a second ECMP path, or when the route has
    # been broken up across lines becuase of the length.
    re_ecmp = r'[ ]*' + re_metric + re_nexthop + re_lifetime + re_interface

    #Compile RegEx expressions
    reSingle = re.compile(re_single)
    reConnected = re.compile(re_connected)
    reMultiline = re.compile(re_multiline)
    reECMP = re.compile(re_ecmp)

    # Start parsing raw route table into a data structure.  Each route entry goes
    # into a dict, and all the entries are collected into a list.
    for entry in routelist:
        routeentry = {}
        regex = reSingle.match(entry)
        if regex:
            # Need to track protocol and network in case the next line is a 2nd
            # equal cost path (which doesn't show that info)
            prev_prot = regex.group('protocol') 
            prev_net = regex.group('network')
            routeentry = {  "protocol" : prev_prot,
                            "network" : prev_net,
                            "AD" : regex.group('ad'),
                            "metric" : regex.group('metric'),
                            "nexthop" : regex.group('nexthop'),
                            "lifetime" : regex.group('lifetime'),
                            "interface" : regex.group('interface')
                            }
        else:
            regex = reConnected.match(entry)
            if regex:
                routeentry = {  "protocol" : regex.group('protocol'),
                                "network" : regex.group('network'),
                                "AD" : 0,
                                "metric" : 0,
                                "nexthop" : None,
                                "interface" : regex.group('interface')
                                }
            else:
                regex = reMultiline.match(entry)
                if regex:
                    # Since this is the first line in an entry that was broken
                    # up due to length, only record protocol and network.
                    # The next line has the rest of the data needed.
                    prev_prot = regex.group('protocol') 
                    prev_net = regex.group('network')
                else:
                    regex = reECMP.match(entry)
                    if regex:
                        # Since this is a second equal cost entry, use
                        # protocol and network info from previous entry
                        routeentry = {  "protocol" : prev_prot,
                                        "network" : prev_net,
                                        "AD" : regex.group('ad'),
                                        "metric" : regex.group('metric'),
                                        "nexthop" : regex.group('nexthop'),
                                        "lifetime" : regex.group('lifetime'),
                                        "interface" : regex.group('interface')
                                        }
        if routeentry != {}:
            routetable.append(routeentry)
    return routetable


def alphanum_key(s):
    '''
    From http://nedbatchelder.com/blog/200712/human_sorting.html
    '''
    return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', s)] 


def NextHopSummary(routelist):
    '''
    This function will take the routelist datastructure (created by ParseRawRoutes) and process it into
    a datastructure containing the summary data, that is then converted to a list so it can be easily written
    into a CSV file (by ListToCSV).
    '''
    def GetProtocol(raw_protocol):
        if raw_protocol[0] == 'S':
            return 'Static'
        elif raw_protocol[0] == 'D':
            return 'EIGRP'
        elif raw_protocol[0] == 'O':
            return 'OSPF'
        elif raw_protocol[0] == 'B':
            return 'BGP'
        elif raw_protocl[0] == 'i':
            return 'ISIS'
        elif raw_protocol[0] == 'R':
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


def ListToCSV(data, filename, suffix=".csv"):
    '''
    This function takes a list and puts it into a CSV file with the supplied 
    filename.  The default suffix is .csv unless a different one is passed in.
    '''
    newfile = open(filename + suffix, 'wb')
    csvOut = csv.writer(newfile)
    for line in data:
        csvOut.writerow(line)
    newfile.close()


def Main():
    '''
    The purpose of this program is to capture the CDP information from the connected
    switch and ouptut it into a CSV file.
    '''
    SendCmd = "show ip route"

    #Create a "Tab" object, so that all the output goes into the correct Tab.
    objTab = crt.GetScriptTab()
    tab = objTab.Screen  #Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"
    tab.Synchronous = True
    tab.IgnoreEscape = True

    #Get the prompt of the device
    hostname = GetHostname(tab)
    prompt = hostname + "#"

    if hostname == None:
        crt.Dialog.MessageBox("Either not in enable mode, or the prompt could not be detected")
    else:
        now = datetime.datetime.now()
        mydate = now.strftime(mydatestr)
        
        #Create Filename
        filebits = [hostname, "nexthops", mydate]
        filename = '-'.join(filebits)
        
        #Create path to save configuration file and open file
        fullFileName = os.path.join(os.path.expanduser('~'), savepath + filename)
        rawRouteFile = fullFileName + ".txt"

        # Save raw "show ip route" output to a file.  Dumping directly to a var has problems when the
        # route table is very large (1000+ lines)
        WriteOutput(SendCmd, rawRouteFile, prompt, tab)

        # Create a list that contains all the route entries (minus their line endings)
        routes = [line.rstrip('\n') for line in open(rawRouteFile)]
        
        routelist = ParseRawRoutes(routes)
        nexthops, connected = NextHopSummary(routelist)
        nexthops.extend(connected)
        ListToCSV(nexthops, fullFileName)
        

    tab.Synchronous = False
    tab.IgnoreEscape = False


Main()
