# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script will grab the detailed CDP information from a Cisco IOS or NX-OS 
# device and export it to a CSV file containing the important information, such
# as Remote Device hostname, model and IP information, in addition to the local
# and remote interfaces that connect the devices.
# 
# The path where the file is saved is specified in the "savepath" variable in
# the Main() function.
# 


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
###############################  END OF SETTINGS ###############################


# Import OS and Sys module to be able to perform required operations for adding
# the script directory to the python path (for loading modules), and manipulating
# paths for saving files.
import os
import sys
import csv
import re

# Add the script directory to the python path (if not there) so we can import 
# modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Imports from common SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import GetFilename
from ciscolib import CaptureOutput
from ciscolib import short_int
from ciscolib import short_name
from ciscolib import DictListToCSV


def ParseCDP(rawdata):
    '''
    This function parses the raw "show cdp neighbors detail" output into
    a data structure (a list of dictionaries) of only the important information,
    which can be more easily used by other functions in the program.
    '''
    def GetSeperator(raw):
        list = raw.split('\n')
        for line in list:
            if "-------" in line:
                return line
        else:
            return None
    regex = {
    "Remote ID" : re.compile(r"Device ID:.*", re.I),
    "IP Address" : re.compile(r"IP\w* address:.*", re.I),
    "Platform" : re.compile(r"Platform:.*,", re.I),
    "Local Intf" : re.compile(r"Interface:.*,", re.I),
    "Remote Intf" : re.compile(r"Port ID.*:.*", re.I)
    }
    devData = []
    empty = re.compile(r"")
    sep = GetSeperator(rawdata)
    data_list = rawdata.split(sep)
    for chunk in data_list:
        devInfo = {}
        chunk = chunk.strip()
        if len(chunk) > 0:
            for name, search in regex.iteritems():
                tempsearch = search.findall(chunk)
                if len(tempsearch) > 0:
                    temp = tempsearch[0].split(":")
                else:
                    temp = ['','']                    
                devInfo[name] = temp[1].strip().strip(',')
            devData.append(devInfo)
    return devData


def Main():
    '''
    The purpose of this program is to capture the CDP information from the connected
    switch and ouptut it into a CSV file.
    '''
    SendCmd = "show cdp neighbors detail"

    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)

    # Generate filename used for output files.
    fullFileName = GetFilename(session, settings, "cdp")

    raw = CaptureOutput(session, SendCmd)

    cdpInfo = ParseCDP(raw)
    field_names =  ['Local Intf', 'Remote ID', 'Remote Intf', 'IP Address', 'Platform']
    DictListToCSV(field_names, cdpInfo, fullFileName)

    # Clean up before exiting
    EndSession(session)


if __name__ == "__builtin__":
    Main()