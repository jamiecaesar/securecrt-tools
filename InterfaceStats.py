# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script will scrape some stats (packets, rate, errors) from all the UP 
# interfaces on the device and put it into a CSV file.  The path where the file 
# is saved is specified in the settings section.
#

# Create data structure (dictionary) that holds our settings
settings = {}
###############################  SCRIPT SETTING  ###############################
#### WHERE TO SAVE FILES:
# Enter the path to the directory where the script output should be stored.
# This can either be a relative path (which will start in the user's home
#   directory) or an absolute path (i.e. C:\Output or /Users/Jamie/Output).
settings['savepath'] = 'Dropbox/SecureCRT/Output/'
# The script will use the correct variable based on which OS is running.
#
#
#### FILENAME FORMAT
# Choose the format of the date string added to filenames created by this script.
# Example = '%Y-%m-%d-%H-%M-%S'
# See the bottom of https://docs.python.org/2/library/datetime.html for all 
# available directives that can be used.
settings['date_format'] = '%Y-%m-%d-%H-%M-%S'
#
#### DELETE TEMP FILES
# This script saves the output into a file so that the output can be worked
# with easier (large outputs going directly into variables can bog down and 
# crash).  If you want to keep the file, set this to False.
settings['delete_temp'] = True
###############################  END OF SETTINGS ###############################


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

# Imports from Cisco SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import DetectNetworkOS
from ciscolib import GetFilename
from ciscolib import WriteOutput
from ciscolib import ReadFileToList
from ciscolib import DictListToCSV


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


def Main():
    SupportedOS = ["IOS", "IOS XE", "NX-OS"]
    

    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)

    # Generate filename used for output files.
    fullFileName = GetFilename(session, settings, "int_summary")

    # Detect and store the OS of the attached device
    DetectNetworkOS(session)

    if session['OS'] in SupportedOS:
        if session['OS'] == "NX-OS":
            SendCmd = "show interface"
            # Save raw output to a file.  Dumping directly to a var has problems with
            # large outputs
            WriteOutput(session, SendCmd, fullFileName)
        
            # Create a list that contains all the route entries (minus their line endings)
            intf_raw = ReadFileToList(fullFileName)
            
            # If the settings allow it, delete the temporary file that holds show cmd output
            if settings['delete_temp']:    
                os.remove(fullFileName + ".txt")

            summarytable = ParseNXOSIntfStats(intf_raw)
            field_names =   [ "Interface", "Description", "InBPS", "InPPS", "OutBPS", "OutPPS", 
                              "InputPackets", "InputErr", "OutputPackets", "OutputErr"]
            DictListToCSV(field_names, summarytable, fullFileName)
        else:
            SendCmd = "show interfaces"
            # Save raw output to a file.  Dumping directly to a var has problems with
            # large outputs
            WriteOutput(session, SendCmd, fullFileName)
        
            # Create a list that contains all the route entries (minus their line endings)
            intf_raw = ReadFileToList(fullFileName)
            
            # If the settings allow it, delete the temporary file that holds show cmd output
            if settings['delete_temp']:    
                os.remove(fullFileName + ".txt")
            
            summarytable = ParseIOSIntfStats(intf_raw)
            field_names =   [ "Interface", "Description", "InBPS", "InPPS", "OutBPS", "OutPPS", 
                              "InputPackets", "InputErr", "OutputPackets", "OutputErr"]
            DictListToCSV(field_names, summarytable, fullFileName)
    else:
        error_str = "This script does not support {}.\n" \
                    "It will currently only run on IOS Devices.".format(session['OS'])
        crt.Dialog.MessageBox(error_str, "Unsupported Network OS", 16)
    
    EndSession(session)


if __name__ == "__builtin__":
    Main()