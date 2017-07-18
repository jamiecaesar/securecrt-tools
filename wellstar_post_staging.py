# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will grab the output for the list of commands in the document_device.json file that should exist in the
# same directory where this script is located.
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
import json

# Add the script directory to the python path (if not there) so we can import custom modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Imports from custom SecureCRT modules
from imports.cisco_securecrt import start_session
from imports.cisco_securecrt import end_session
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import write_output_to_file
from imports.cisco_securecrt import ICON_INFO


# #################################  SCRIPT  ###################################


def main():
    """
    Captures the output from "show running-config" and saves it to a file.
    """

    # Import JSON file containing list of commands that need to be run.  If it does not exist, create one and use it.
    command_list = None
    command_list_filename = crt.ScriptFullName.replace(".py", ".json")
    command_list_full_path = os.path.join(script_dir, command_list_filename)
    if os.path.isfile(command_list_full_path):
        with open(command_list_full_path, 'r') as json_file:
            command_list = json.load(json_file)
    else:
        command_list = ["show ver", "show int status", "show run"]
        with open(command_list_full_path, 'w') as json_file:
            json.dump(command_list, json_file, indent=4, separators=(',', ': '))

        setting_msg = ("A file containing the commands to capture, {}, has been created at:\n'{}'\n\n"
                       "Please edit this file to change the list of commands."
                       ).format(command_list_full_path, script_dir)
        crt.Dialog.MessageBox(setting_msg, "Settings Created", ICON_INFO)

    # Run session start commands and save session information into a dictionary
    session = start_session(crt, script_dir)

    for command in command_list:

        # Generate filename used for output files.
        full_file_name = create_output_filename(session, "STAGED-{}".format(command))

        # Get the output of our command and save it to the filename specified
        write_output_to_file(session, command, full_file_name)

    # Clean up before closing session
    end_session(session)

if __name__ == "__builtin__":
    main()