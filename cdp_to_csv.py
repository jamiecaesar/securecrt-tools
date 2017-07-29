# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will grab the detailed CDP information from a Cisco IOS or NX-OS device and export it to a CSV file
# containing the important information, such as Remote Device hostname, model and IP information, in addition to the
# local and remote interfaces that connect the devices.
# 
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
from imports.cisco_securecrt import list_of_lists_to_csv

from imports.cisco_tools import get_template_full_path
from imports.cisco_tools import textfsm_parse_to_list
from imports.cisco_tools import extract_system_name


##################################  SCRIPT  ###################################


def main():
    """
    Capture the CDP information from the connected device and ouptut it into a CSV file. 
    """
    # Extract the script name from the full script path.
    script_name = crt.ScriptFullName.split(os.path.sep)[-1]

    # Create settings filename by replacing .py in script name with .json
    local_settings_file = script_name.replace(".py", ".json")

    # Define what local settings should be by default - REQUIRES __version
    local_settings_default = {'__version': "1.0",
                              '_strip_domains_comment': "A list of strings to remove if found in the device ID of CDP "
                                                        "output.  Configurable due to '.' being a valid hostname "
                                                        "character and doesn't always signify a component of FQDN.",
                              'strip_domains': [".cisco.com"]
                              }
    # Define the directory to save the settings file in.
    settings_dir = os.path.normpath(os.path.join(script_dir, "settings"))

    # Import JSON file containing list of commands that need to be run.  If it does not exist, create one and use it.
    local_settings = load_settings(crt, settings_dir, local_settings_file, local_settings_default)

    if local_settings:
        send_cmd = "show cdp neighbors detail"

        # Run session start commands and save session information into a dictionary
        session = start_session(crt, script_dir)

        # Make sure we completed session start.  If not, we'll receive None from start_session.
        if session:
            # Build full path to template file for TextFSM
            cdp_template = "cisco_os_show_cdp_neigh_det.template"
            # Build path to template, process output and export to CSV
            template_path = get_template_full_path(session, cdp_template)

            # Capture output from our command and write to a temporary file
            temp_filename = create_output_filename(session, "cdp")
            write_output_to_file(session, send_cmd, temp_filename)

            # Use TextFSM to parse our output from the temporary file, and delete it.
            with open(temp_filename, 'r') as cdp_data:
                cdp_table = textfsm_parse_to_list(cdp_data, template_path, add_header=True)
            os.remove(temp_filename)

            # Since "System Name" is a newer NXOS feature -- try to extract it from the device ID when its empty.
            for entry in cdp_table:
                # entry[2] is system name, entry[1] is device ID
                if entry[2] == "":
                    entry[2] = extract_system_name(entry[1], strip_list=local_settings['strip_domains'])

            # Write TextFSM output to a .csv file.
            output_filename = create_output_filename(session, "cdp", ext=".csv")
            list_of_lists_to_csv(session, cdp_table, output_filename)

            # Clean up before exiting
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
