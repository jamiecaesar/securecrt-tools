# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script will grab the running configuration of a Cisco IOS or NX-OS device
# and save it into a file.
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

##################################  SCRIPT  ###################################

def Main():
    '''
    This purpose of this program is to capture the output of the "show run" command and
    save it to a file.  This method is much faster than manually setting a log file, or 
    trying to extract the information from a log file.
    '''
    SendCmd = "show run"

    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)

    # Generate filename used for output files.
    fullFileName = GetFilename(session, settings, "show-run")

    # Get the output of our command and save it to the filename specified
    WriteOutput(session, SendCmd, fullFileName)

    # Clean up before closing session
    EndSession(session)

if __name__ == "__builtin__":
    Main()