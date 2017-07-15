# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
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
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import write_output_to_file


# #################################  SCRIPT  ###################################


def main():
    """
    Captures the output from "show running-config" and saves it to a file.
    """
    send_cmd = "show running-config"

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Generate filename used for output files.
    full_file_name = create_output_filename(session, "show-run")

    # Get the output of our command and save it to the filename specified
    write_output_to_file(session, send_cmd, full_file_name)

    # Clean up before closing session
    end_session(session)

if __name__ == "__builtin__":
    main()