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
import csv
import re

# Add the script directory to the python path (if not there) so we can import 
# modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import Settings from Settings File or Default settings
try:
    from script_settings import settings
except ImportError:
    import shutil
    src_file = os.path.join(script_dir, 'script_settings_default.py')
    dst_file = os.path.join(script_dir, 'script_settings.py')
    try:
        shutil.copy(src_file, dst_file)
        setting_msg = ("Personal settings file created in directory:\n'{}'\n\n"
                       "Please edit this file to make any settings changes."
                       ).format(script_dir)
        crt.Dialog.MessageBox(setting_msg, "Settings Created", 64)
        from script_settings import settings
    except IOError, ImportError:
        err_msg =   ('Cannot find settings file.\n\nPlease make sure either the file\n'
                    '"script_settings_default.py"\n exists in the directory:\n"{}"\n'.format(script_dir)
                    )
        crt.Dialog.MessageBox(str(err_msg), "Settings Error", 16)
        exit(0)

# Imports from common SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import GetFilename
from ciscolib import WriteOutput
from ciscolib import short_int
from ciscolib import short_name
from ciscolib import DictListToCSV

##################################  SCRIPT  ###################################

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

    WriteOutput(session, SendCmd, fullFileName)

    with open(fullFileName + ".txt", 'r') as newfile:
        raw = newfile.read()

    # If the settings allow it, delete the temporary file that holds show cmd output
    if settings['delete_temp']:    
        os.remove(fullFileName + ".txt")
        
    cdpInfo = ParseCDP(raw)
    field_names =  ['Local Intf', 'Remote ID', 'Remote Intf', 'IP Address', 'Platform']
    DictListToCSV(field_names, cdpInfo, fullFileName)

    # Clean up before exiting
    EndSession(session)


if __name__ == "__builtin__":
    Main()