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
# 
# This script is tested on SecureCRT version 7.2 on OSX Mavericks

import os
import datetime
import csv
import re
import pickle
import sys

savepath = 'Dropbox/SecureCRT/Backups/'
mydatestr = '%Y-%m-%d-%H-%M-%S'

def GetHostname(tab):
    '''
    This function will capture the prompt of the device, by capturing the text
    returned after sending a couple line feeds.  Because the script will keep
    running commands before the commands we send are echo'd back to us, we
    have to add some "WaitForString"s so we capture only what we want.
    '''
    #Send two line feeds
    tab.Send("\n\n")
    tab.WaitForString("\n") # Waits for first linefeed to be echoed back to us
    prompt = tab.ReadString("\n") #Read the text up to the next linefeed.
    prompt = prompt.strip() #Remove any trailing control characters
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


def CaptureOutput(command, prompt, tab):
    '''
    This function captures the raw output of the command supplied and returns it.
    The prompt variable is used to signal the end of the command output, and 
    the "tab" variable is object that specifies which tab the commands are 
    written to. 
    '''
    #Send term length command and wait for prompt to return
    tab.Send('term length 0\n')
    tab.WaitForString(prompt)
    
    #Send command
    tab.Send(command + "\n")

    #Ignore the echo of the command we typed
    tab.WaitForString(command)
    
    #Capture the output until we get our prompt back and write it to the file
    result = tab.ReadString(prompt)

    #Send term length back to default
    tab.Send('term length 24\n')
    tab.WaitForString(prompt)

    return result


def ParseRawRoutes(routelist):
    DEBUG = False
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
    re_interface = r'(?P<interface>\w+(/\d)*)?'

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
                    else:
                        if DEBUG:
                            print "Skipping: " + entry
        if routeentry != {}:
            routetable.append(routeentry)
    return routetable


def NextHopSummary(routelist):
    summaryDict = {}
    for entry in routelist:
        if entry['nexthop']:
            if entry['nexthop'] in summaryDict:
                summaryDict[entry['nexthop']] += 1
            else:
                summaryDict[entry['nexthop']] = 1
    nexthops = [['Next-hop', '# of routes']]
    for key, value in summaryDict.iteritems():
        nexthops.append([key, value])
    return nexthops


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

        raw = CaptureOutput(SendCmd, prompt, tab)

        routes = raw.split('\r\n')
        routelist = ParseRawRoutes(routes)
        summary = NextHopSummary(routelist)
        ListToCSV(summary, fullFileName)
        

    tab.Synchronous = False
    tab.IgnoreEscape = False


Main()
