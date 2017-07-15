# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: XXXXXXXX
# Email: XXXXXXX@presidio.com
# 
# This script will grab the running configuration of a Cisco IOS or NX-OS device and save it into a file.
#

# ##############################  SCRIPT SETTING  ###############################
#
# Settings for this script are saved in the "script_settings.json" file that should be located in the same directory as
# this script.
#


# #################################  IMPORTS  ##################################
# Import OS and Sys module to be able to perform required operations for adding the script directory to the python
# path (for loading modules), and manipulating paths for saving files.
import os
import sys

# Add the script directory to the python path (if not there) so we can import custom modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Imports from custom SecureCRT modules
from imports.cisco_securecrt import start_session
from imports.cisco_securecrt import end_session


# #################################  SCRIPT  ###################################


def main():
        """
        Put a description of what the script will do here
        """

        # Run session start commands and save session information into a dictionary
        session = start_session(crt, script_dir)

        #    
        # PUT YOUR CODE HERE
        #

        # Clean up before closing session
        end_session(session)

if __name__ == "__builtin__":
    main()