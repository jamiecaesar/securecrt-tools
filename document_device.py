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
# Global settings that affect all scripts (output directory, date format, etc) is stored in the "global_settings.json"
# file in the "settings" directory.
#
# If any local settings are used for this script, they will be stored in the same settings folder, with the same name
# as the script that uses them, except ending with ".json".
#
# All settings can be manually modified with the same syntax as Python lists and dictionaries.   Be aware of required
# commas between items, or else options are likely to get run together and neither will work.
#
# **IMPORTANT**  All paths saved in .json files must contain either forward slashes (/home/jcaesar) or
# DOUBLE back-slashes (C:\\Users\\Jamie).   Single backslashes will be considered part of a control character and will
# cause an error on loading.
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
from imports.cisco_securecrt import load_settings
from imports.cisco_securecrt import generate_settings
from imports.cisco_securecrt import write_settings
from imports.cisco_securecrt import create_output_filename
from imports.cisco_securecrt import write_output_to_file
from imports.cisco_securecrt import ICON_INFO


# #################################  SCRIPT  ###################################


def main():
    """
    Captures the output from "show running-config" and saves it to a file.
    """
    # Extract the script name from the full script path.
    script_name = crt.ScriptFullName.split(os.path.sep)[-1]

    # Create settings filename by replacing .py in script name with .json
    local_settings_file = script_name.replace(".py", ".json")

    supported_os = ["IOS", "NX-OS", "ASA"]
    # Define what local settings should be by default - REQUIRES __version
    local_settings_default = {"__version": "1.0",
                              "IOS": ["show ver",
                                      "show int status",
                                      "show run",
                                      "show standby brief"],
                              "NX-OS": ["show ver",
                                        "show int status",
                                        "show run",
                                        "show hsrp brief"],
                              "ASA": ["show ver",
                                      "show run"]
                              }

    # Define the directory to save the settings file in.
    settings_dir = os.path.normpath(os.path.join(script_dir, "settings"))

    # Import JSON file containing list of commands that need to be run.  If it does not exist, create one and use it.
    local_settings = load_settings(crt, settings_dir, local_settings_file, local_settings_default)

    if local_settings:
        # Run session start commands and save session information into a dictionary
        session = start_session(crt, script_dir)

        device_os = session['OS']
        if device_os in supported_os:
            command_list = local_settings[device_os]
        else:
            crt.Dialog.MessageBox("This device OS isn't supported by this script.  Exiting.")
            return

        # Make sure we completed session start.  If not, we'll receive None from start_session.
        if session:
            for command in command_list:

                # Generate filename used for output files.
                full_file_name = create_output_filename(session, command)

                # Get the output of our command and save it to the filename specified
                write_output_to_file(session, command, full_file_name)

            # Clean up before closing session
            end_session(session)
    else:
        new_settings = generate_settings(local_settings_default)
        write_settings(crt, settings_dir, local_settings_file, new_settings)
        setting_msg = ("Script specific settings file, {0}, created in directory:\n'{1}'\n\n"
                       "Please edit this file to make any settings changes.\n\n"
                       "After editing the settings, please run the script again."
                       ).format(local_settings_file, settings_dir)
        crt.Dialog.MessageBox(setting_msg, "Script-Specific Settings Created", ICON_INFO)
        return

if __name__ == "__builtin__":
    main()
