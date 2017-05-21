# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This SecureCRT script will prompt the user for a command to a Cisco IOS or NX-OS device and dump the output to a
# file.  The path where the file is saved is specified in the "savepath" variable in the Main() function.
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
    Prompts for a command and captures the output of that command to a file
    
    Filename is based on hostname, the command name, and the date string defined in the settings file.
    """
    send_cmd = crt.Dialog.Prompt("Enter the command to capture")

    if send_cmd == "":
        return
    else:
        # Save command without spaces to use in output filename.
        cmd_desc = send_cmd.replace(" ", "_")
        # Add a newline to command before sending it to the remote device.

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    # Generate filename used for output files.
    full_file_name = create_output_filename(session, cmd_desc)

    # Get the output of our command and save it to the filename specified
    write_output_to_file(session, send_cmd, full_file_name)

    # Clean up before closing session
    end_session(session)

if __name__ == "__builtin__":
    main()
