# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script give a list of VLANs on the switch and how.  These are considered
# ports where either the port is up and the MAC address attached if possible.
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
from ciscolib import FixedColumnsToList
from ciscolib import ListToCSV

##################################  SCRIPT  ###################################

def PortCountList(vlan_table):
    '''
    A function that returns a new list that has a count for the number of
    interfaces assigned to each VLAN, instead of a list of each interface.
    '''
    # Copy the header row to the new list.
    new_list = vlan_table[0:1]

    # Check every line in the original table, except the first
    for line in vlan_table[1:]:
        # Copy the first 3 elements to the new line (VLAN, Name, Status)
        new_line = line[:3]
        # If there is a list of interfaces, get the count.  Otherwise 
        # either ignore or create a line with '0', depeding on settings.
        if line[3]:
            port_list = line[3].split(', ')
            new_line.append(str(len(port_list)))
            new_list.append(new_line)
        elif settings['show_all_VLANs']:
            new_line.append('0')
            new_list.append(new_line)
    return new_list


def Main():

    SendCmd = "show vlan brief"
    show_vlan_widths = (5, 33, 10, -1)
    
    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)

    # Generate filename used for output files.
    fullFileName = GetFilename(session, settings, "ActiveVLANs")
    
    # Save raw output to a file.  Dumping directly to a var has problems with
    # large outputs
    WriteOutput(session, SendCmd, fullFileName)

    # Get a list version of the VLAN table
    vlan_table = FixedColumnsToList(fullFileName, show_vlan_widths, ext='.txt')

    # Depending on settings, delete temporary storage of "show vlan" output
    if settings['delete_temp']:    
        os.remove(fullFileName + ".txt")

    # Get a table that shows the count of assigned ports, not the names.
    vlan_summary = PortCountList(vlan_table)

    # Write data into a CSV file.
    ListToCSV(vlan_summary, fullFileName)
        
    # Clean up before exiting
    EndSession(session)


if __name__ == "__builtin__":
    Main()