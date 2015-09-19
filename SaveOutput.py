# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This SecureCRT script will prompt the user for a command to a Cisco IOS or NX-OS 
# device and dump the output to a file.  The path where the file is saved is
# specified in the "savepath" variable in the Main() function.
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


def Main():
    '''
    This purpose of this program is to capture the output of the command entered by the
    user and save it to a file.  This method is much faster than manually setting a log
    file, or trying to extract only the information needed from the saved log file.
    '''
    SendCmd = crt.Dialog.Prompt("Enter the command to capture")
    if SendCmd == "":
        return
    else:
        # Save command without spaces to use in output filename.
        CmdName = SendCmd.replace(" ", "_")
        # Add a newline to command before sending it to the remote device.
        SendCmd = SendCmd + "\r\n"

    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)

    # Generate filename used for output files.
    fullFileName = GetFilename(session, settings, CmdName)

    # Get the output of our command and save it to the filename specified
    WriteOutput(session, SendCmd, fullFileName)

    # Clean up before closing session
    EndSession(session)

if __name__ == "__builtin__":
    Main()
