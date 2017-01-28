# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Michael Ethridge
#
# This script will grab the dynamic MAC table information from a Cisco IOS
# device and export it to a CSV file containing the VLAN, MAC and Interface.
#
# The path where the file is saved is specified in the "savepath" variable in
# the Main() function.
#


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

# Imports from common SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import GetFilename
from ciscolib import WriteOutput
from ciscolib import DictListToCSV
from ciscolib import ReadFileToList

##################################  SCRIPT  ###################################

def ParseMAC(rawdata):
    '''
    This function parses the raw "show mac address dynamic | exclude Po" output into
    a data structure (a list of dictionaries) of only the important information,
    which can be more easily used by other functions in the program.

    The data structure that is returned in a list of dictionaries.  Each dictionary
    entry represents an entry in the mac table and contains the following keys:

    {"VLAN", "MAC", "Interface"}

    '''

    mactable = []

    # Matches VLAN id: 100
    re_vlan = r'^\s*(?P<vlan>[0-9]{1,4})\s+'
    # Matches MAC: xxxx.xxxx.xxxx
    re_mac = r'(?P<mac>[0-9,a-f]{4}\.[0-9,a-f]{4}\.[0-9,a-f]{4})\s+'
    # Matches Dynamic type: DYNAMIC
    re_type = r'DYNAMIC\s+'
    # Matches Interface: Gi1/0/1
    re_interface = r'(?P<interface>[\w-]+[\/\.\d]*)?'

    # Combining expressions above to build possible lines found in the mac table
    #
    re_mac_entry = re_vlan + re_mac + re_type + re_interface

    #Compile RegEx expressions
    reMAC = re.compile(re_mac_entry)

    for entry in rawdata:
        macentry = {}
        regex = reMAC.match(entry)
        if regex:
            macentry = {
                "VLAN" : regex.group('vlan'),
                "MAC" : regex.group('mac'),
                "Interface" : regex.group('interface')
            }
        if macentry != {}:
            mactable.append(macentry)
    return mactable


def Main():
    '''
    The purpose of this program is to capture the MAC Table information from the connected
    switch excluding the Port-Channels (Uplinks) and ouptut it into a CSV file.
    '''
    SendCmd = 'show mac address- dynamic | exclude Po'

    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)
    settings = session['settings']

    # Generate filename used for output files.
    fullFileName = GetFilename(session, settings, "mac-addresses")

    # Save raw "show mac address dynamic | exclude Po" output to a file.  Dumping directly
    # to a huge string has problems when the mac table is large (1000+ lines)
    WriteOutput(session, SendCmd, fullFileName)

    macs = ReadFileToList(fullFileName)

    macInfo = ParseMAC(macs)

    # If the settings allow it, delete the temporary file that holds show cmd output
    if settings['delete_temp']:
        os.remove(fullFileName + ".txt")

    field_names =  ['VLAN', 'MAC', 'Interface']
    DictListToCSV(field_names, macInfo, fullFileName)

    # Clean up before exiting
    EndSession(session)


if __name__ == "__builtin__":
    Main()