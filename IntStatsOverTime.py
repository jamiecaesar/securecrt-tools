# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script will record interface statistics (if the interface is "up") every
# X seconds, for Y number of samples.  X and Y can be changed in the local
# settings section below.

# The data is output as a CSV file in a
# table layout, where each row is an interface, and each column is the value
# at a particular timestamp.  Each statistic (Input bps, Input pps, etc) is
# written as a separate table in the file.
#
# This CSV file can be opened in Excel, allowing the user to select the data
# for one type of statistic, and insert a line graph to automatically generate
# a graph with each line corresponding to an interface, and each point for a 
# line is the value at a particular point in time.

##############################  GLOBAL SETTING  ###############################
#
# Settings that are referenced by all scripts (save location, etc) are saved in 
# the "script_settings.py" file that should be located in the same directory as 
# this script.
#

###############################  LOCAL SETTING  ###############################
# Below are local settings use specifically for this script.
#

# Stats that we are interested in capture data over time for

measurements = [    "InBPS",            #Bits per second, Inbound
                    "OutBPS",           #Bits per second, Outbound
                    "InPPS",            #Packets per second, Inbound
                    "OutPPS",           #Packets per second, Outbound
                    #"InputPackets",    #Total Packets Input
                    "InputErr",         #Input Errors
                    #"OutputPackets",   #Total Packets Output
                    "OutputErr"         #Output Errors
]

# Time between samples (in seconds)
interval = 30

# Total number of samples to take.
stat_count = 12



##################################  IMPORTS  ##################################
# Import OS and Sys module to be able to perform required operations for adding
# the script directory to the python path (for loading modules), and manipulating
# paths for saving files.
import os
import sys
import re
import time
from datetime import datetime
import pprint

# Add the script directory to the python path (if not there) so we can import 
# modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import Settings from Settings File or Default settings
try:
    from script_settings import settings
except IOError:
    from script_settings_default import settings

# Imports from Cisco SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import DetectNetworkOS
from ciscolib import GetFilename
from ciscolib import WriteOutput
from ciscolib import ReadFileToList
from ciscolib import ListToCSV
from ciscolib import DictListToCSV
from ciscolib import alphanum_key

##################################  SCRIPT  ###################################

def ParseIOSIntfStats(raw_int_output):
    '''
    This function parses the raw show interface output into a datastucture that can be used 
    to more easily extract information.  The data structure that is returned in a list of 
    dictionaries.
    '''
    intftable = []
    # Various RegEx expressions to match varying parts of a show int line
    # I did it this way to break up the regex into more manageable parts, 
    # Plus some of these parts can be found in multiple line types
    # I'm also using named groups to more easily extract the needed data.
    #
    # Interface Name (only capture interfaces that are up)
    re_intf = r'(?P<Interface>[\w\/\.-]*) is up, line protocol is up'
    re_desc = r'.*Description: (?P<desc>.*)' 
    re_inrate = r'.*input rate (?P<InBPS>\d*) bits\/sec, (?P<InPPS>\d*) packets\/sec'
    re_outrate = r'.*output rate (?P<OutBPS>\d*) bits\/sec, (?P<OutPPS>\d*) packets\/sec'
    re_inpkts = r'\W*(?P<InPackets>\d*) packets input.*'
    re_inerr = r'\W*(?P<InputErr>\d*) input error.*'
    re_outpkts = r'\W*(?P<OutPackets>\d*) packets output.*'
    re_outerr = r'\W*(?P<OutputErr>\d*) output error.*'

    #Compile RegEx expressions
    reIntf = re.compile(re_intf)
    reDesc = re.compile(re_desc)
    reInRate = re.compile(re_inrate)
    reOutRate = re.compile(re_outrate)
    reInPkts = re.compile(re_inpkts)
    reInErr = re.compile(re_inerr)
    reOutPkts = re.compile(re_outpkts)
    reOutErr = re.compile(re_outerr)

    # Start parsing raw interface output into a data structure.  Each int entry goes
    # into a dict, and all the entries are collected into a list.
    intfentry = {   "Interface" : None,
                    "Description" : None,
                    "InBPS" : None,
                    "InPPS" : None,
                    "OutBPS" : None,
                    "OutPPS" : None,
                    "InputPackets" : None,
                    "InputErr" : None,
                    "OutputPackets" : None,
                    "OutputErr" : None
                }
    for line in raw_int_output:
        # Check if this is the start of a new interface block
        line = line.strip()
        regex = reIntf.match(line)
        if regex:
            # If so, write the previous block and reset
            if intfentry['Interface'] is not None:
                intftable.append(intfentry)
                intfentry = {   "Interface" : regex.group('Interface'),
                                "Description" : None,
                                "InBPS" : None,
                                "InPPS" : None,
                                "OutBPS" : None,
                                "OutPPS" : None,
                                "InputPackets" : None,
                                "InputErr" : None,
                                "OutputPackets" : None,
                                "OutputErr" : None
                            }
            else:
                # If so, but the current intfentry doesn't have an interface name assigned yet
                intfentry['Interface'] = regex.group('Interface')
        
        elif "Description" in line:
            regex = reDesc.match(line)
            if regex:
                intfentry['Description'] = regex.group('desc')
        elif intfentry['InBPS'] is None:
            regex = reInRate.match(line)
            if regex:
                intfentry['InBPS'] = regex.group('InBPS')
                intfentry['InPPS'] = regex.group('InPPS')
        elif intfentry['OutBPS'] is None:
            regex = reOutRate.match(line)
            if regex:
                intfentry['OutBPS'] = regex.group('OutBPS')
                intfentry['OutPPS'] = regex.group('OutPPS')
        elif intfentry['InputPackets'] is None:
            regex = reInPkts.match(line)
            if regex:
                intfentry['InputPackets'] = regex.group('InPackets')  
        elif intfentry['InputErr'] is None:
            regex = reInErr.match(line)
            if regex:
                intfentry['InputErr'] = regex.group('InputErr')
        elif intfentry['OutputPackets'] is None:
            regex = reOutPkts.match(line)
            if regex:
                intfentry['OutputPackets'] = regex.group('OutPackets')  
        elif intfentry['OutputErr'] is None:
            regex = reOutErr.match(line)
            if regex:
                intfentry['OutputErr'] = regex.group('OutputErr')
    # If we reached the end, write the final entry
    if intfentry['Interface'] is not None:
        intftable.append(intfentry) 
    return intftable


def ParseNXOSIntfStats(raw_int_output):
    '''
    This function parses the raw show interface output into a datastucture that can be used 
    to more easily extract information.  The data structure that is returned in a list of 
    dictionaries.
    '''
    intftable = []
    # Various RegEx expressions to match varying parts of a show int line
    # I did it this way to break up the regex into more manageable parts, 
    # Plus some of these parts can be found in multiple line types
    # I'm also using named groups to more easily extract the needed data.
    #
    # Interface Name (only capture interfaces that are up)
    re_intf = r'(?P<Interface>[\w\/\.-]*) is up.*'
    re_desc = r'.*Description: (?P<desc>.*)' 
    re_inrate = r'.*input rate (?P<InBPS>\d*) bits\/sec, (?P<InPPS>\d*) packets\/sec'
    re_outrate = r'.*output rate (?P<OutBPS>\d*) bits\/sec, (?P<OutPPS>\d*) packets\/sec'
    re_inpkts = r'(?P<InPackets>\d*) input packets.*'
    re_inerr = r'(?P<InputErr>\d*) input error.*'
    re_outpkts = r'(?P<OutPackets>\d*) output packets.*'
    re_outerr = r'(?P<OutputErr>\d*) output error.*'

    #Compile RegEx expressions
    reIntf = re.compile(re_intf)
    reDesc = re.compile(re_desc)
    reInRate = re.compile(re_inrate)
    reOutRate = re.compile(re_outrate)
    reInPkts = re.compile(re_inpkts)
    reInErr = re.compile(re_inerr)
    reOutPkts = re.compile(re_outpkts)
    reOutErr = re.compile(re_outerr)

    # Start parsing raw interface output into a data structure.  Each int entry goes
    # into a dict, and all the entries are collected into a list.
    intfentry = {   "Interface" : None,
                    "Description" : None,
                    "InBPS" : None,
                    "InPPS" : None,
                    "OutBPS" : None,
                    "OutPPS" : None,
                    "InputPackets" : None,
                    "InputErr" : None,
                    "OutputPackets" : None,
                    "OutputErr" : None
                }
    for line in raw_int_output:
        # Check if this is the start of a new interface block
        line = line.strip()
        regex = reIntf.match(line)
        # If we get a match on the "interface is up" line, and the line does NOT contain "Vlan"
        # (because Vlan interfaces don't have stats)
        if regex and "Vlan" not in line:
            # If so, write the previous block and reset
            if intfentry['Interface'] is not None:
                intftable.append(intfentry)
                intfentry = {   "Interface" : regex.group('Interface'),
                                "Description" : None,
                                "InBPS" : None,
                                "InPPS" : None,
                                "OutBPS" : None,
                                "OutPPS" : None,
                                "InputPackets" : None,
                                "InputErr" : None,
                                "OutputPackets" : None,
                                "OutputErr" : None
                            }
            else:
                # If so, but the current intfentry doesn't have an interface name assigned yet
                intfentry['Interface'] = regex.group('Interface')
        
        elif "Description" in line:
            regex = reDesc.match(line)
            if regex:
                intfentry['Description'] = regex.group('desc')
        elif intfentry['InBPS'] is None:
            regex = reInRate.match(line)
            if regex:
                intfentry['InBPS'] = regex.group('InBPS')
                intfentry['InPPS'] = regex.group('InPPS')
        elif intfentry['OutBPS'] is None:
            regex = reOutRate.match(line)
            if regex:
                intfentry['OutBPS'] = regex.group('OutBPS')
                intfentry['OutPPS'] = regex.group('OutPPS')
        elif intfentry['InputPackets'] is None:
            regex = reInPkts.match(line)
            if regex:
                intfentry['InputPackets'] = regex.group('InPackets')  
        elif intfentry['InputErr'] is None:
            regex = reInErr.match(line)
            if regex:
                intfentry['InputErr'] = regex.group('InputErr')
        elif intfentry['OutputPackets'] is None:
            regex = reOutPkts.match(line)
            if regex:
                intfentry['OutputPackets'] = regex.group('OutPackets')  
        elif intfentry['OutputErr'] is None:
            regex = reOutErr.match(line)
            if regex:
                intfentry['OutputErr'] = regex.group('OutputErr')
    # If we reached the end, write the final entry
    if intfentry['Interface'] is not None:
        intftable.append(intfentry) 
    return intftable


def Main():

    def GetInterfaceSamples(ParseIntfStats):
        for i in range(stat_count):
            sample_time = datetime.now().strftime("%I:%M:%S")
            timestamps.append(sample_time)

            start = time.clock()
            # Generate filename used for output files.
            fullFileName = GetFilename(session, settings, "int_summary")

            # Save raw output to a file.  Dumping directly to a var has problems with
            # large outputs
            tab.Send('\n')
            WriteOutput(session, SendCmd, fullFileName)

            if stat_count != (i + 1):
                # Print status to the Cisco prompt to keep user aware of progress
                # This must start with ! to be a Cisco comment, to prevent in-terminal errors
                warning_msg = "! {0} samples left. DO NOT TYPE IN WINDOW.".format(stat_count - (i + 1))
                tab.Send(warning_msg + '\n')
                tab.WaitForString(session['prompt'])

            # Read text file into a list of lines (no line endings)
            intf_raw = ReadFileToList(fullFileName)

            # If the settings allow it, delete the temporary file that holds show cmd output
            if settings['delete_temp']:    
                os.remove(fullFileName + ".txt")

            summarytable = ParseIntfStats(intf_raw)

            for stat in measurements:
                for entry in summarytable:
                    if entry['Interface'] in output[stat]:
                        output[stat][entry['Interface']][sample_time] = entry[stat]
                    else:
                        output[stat][entry['Interface']] = {}
                        output[stat][entry['Interface']][sample_time] = entry[stat]

            end = time.clock()
            if interval - (end - start) > 0:
                if stat_count != (i + 1):
                    time.sleep(interval - (end - start))
            else:
                 crt.Dialog.MessageBox("Did not complete within interval time", 
                                    "Took Too Long", ICON_STOP)
                 sys.exit(0)


    SupportedOS = ["IOS", "IOS XE", "NX-OS"]
    
    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)
    SendCmd = "show interface"
    tab = session['tab']

    output = {}
    for name in measurements:
        output[name] = {}

    timestamps = []

    if session['OS'] in SupportedOS:
        if session['OS'] == "NX-OS":
            GetInterfaceSamples(ParseNXOSIntfStats)
        else:
            GetInterfaceSamples(ParseIOSIntfStats)
    else:
        error_str = "This script does not support {}.\n" \
                    "It will currently only run on IOS Devices.".format(session['OS'])
        crt.Dialog.MessageBox(error_str, "Unsupported Network OS", 16)
    
    field_names = [ "Interface" ]
    field_names.extend(timestamps)

    fullFileName = GetFilename(session, settings, "graph")
    
    for stat in measurements:
        temp_csv_list = []
        header = [ [stat] ]
        empty_line = [ [] ] 
        for key in sorted(output[stat].keys(), key=alphanum_key):
            temp_dict = { "Interface" : key }
            temp_dict.update(output[stat][key])
            temp_csv_list.append(temp_dict)
        ListToCSV(header, fullFileName, mode='ab')
        DictListToCSV(field_names, temp_csv_list, fullFileName, mode='ab')
        # Add seperator line
        ListToCSV(empty_line, fullFileName, mode='ab')

    EndSession(session)
    crt.Dialog.MessageBox("Interface Statistic Gathering Complete", "Script Complete", 64)


if __name__ == "__builtin__":
    Main()