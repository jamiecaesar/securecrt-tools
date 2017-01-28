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
    settings = session['settings']

    # Generate filename used for output files.
    fullFileName = GetFilename(session, settings, "show-run")

    # Get the output of our command and save it to the filename specified
    WriteOutput(session, SendCmd, fullFileName)

    # Clean up before closing session
    EndSession(session)

if __name__ == "__builtin__":
    Main()