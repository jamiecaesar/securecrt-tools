# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ###############################
# Author: Michael Ethridge
# Email: michael@methridge.com
#
# This script will import a list of sessions to create in SecureCRT from a CSV
# file.
#

# ##############################  SCRIPT SETTING  #############################
#
# Global settings that affect all scripts (output directory, date format, etc)
# is stored in the "global_settings.json" file in the "settings" directory.
#
# If any local settings are used for this script, they will be stored in the
# same settings folder, with the same name as the script that uses them,
# except ending with ".json".
#
# All settings can be manually modified with the same syntax as Python lists
# and dictionaries.   Be aware of required commas between items, or else
# options are likely to get run together and neither will work.
#
# **IMPORTANT**  All paths saved in .json files must contain either forward
# slashes (/home/jcaesar) or DOUBLE back-slashes (C:\\Users\\Jamie).
# Single backslashes will be considered part of a control character and will
# cause an error on loading.
#


# #################################  IMPORTS  #################################
# Import OS and Sys module to be able to perform required operations for adding
# the script directory to the python path (for loading modules), and
# manipulating paths for saving files.
import os
import sys

# Add the script directory to the python path (if not there) so we can import
# custom modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Imports from custom SecureCRT modules
from imports.cisco_securecrt import start_session
from imports.cisco_securecrt import end_session
from imports.cisco_securecrt import create_session

# Module specific Imports
import csv


# #################################  SCRIPT  ##################################


def main():
        """
        This script will import a list of sessions to create in SecureCRT from
        a CSV file.
        """

        # Create simple Session DICT so we don't have to be connected to a
        # Device
        session = {'crt': crt}

        # Get input CSV, must contain Session Name and IP.  Can also have
        # Protocol and folder
        sessions_csv = ""
        sessions_csv = crt.Dialog.FileOpenDialog(
            "Please select your CSV Import file",
            "Open",
            sessions_csv,
            "CSV Files (*.csv)|*.csv|"
        )

        # Check if got an input file name or not
        if sessions_csv != "":
            # Set couters
            count = 0
            skipped = 0

            # Open our input file
            with open(sessions_csv, 'rb') as csv_import_file:
                # Read in CSV as DICT
                import_reader = csv.DictReader(csv_import_file)
                # Process each row and create the session
                for row in import_reader:
                    # If we don't have a hostname / IP skip the row
                    if row['hostname'] == "":
                        skipped += 1
                        continue
                    # If session name is blank, set it to hostname / IP
                    if row['session_name'] == "":
                        row['session_name'] = row['hostname']
                    # If protocol is blank set to SSH2
                    if row['protocol'] == "":
                        row['protocol'] = "SSH2"
                    # If folder is blank set to '_imports'
                    if row['folder'] == "":
                        row['folder'] = "_imports"
                    # Create Session
                    create_session(
                        session,
                        row['session_name'],
                        row['hostname'],
                        row['protocol'],
                        row['folder']
                    )
                    count += 1

            # Display summary of created / skipped sessions
            setting_msg = "{0} sessions created\n" \
                          "{1} sessions skipped (no Hostname / IP)" \
                .format(count, skipped)
            crt.Dialog.MessageBox(setting_msg, "Sessions Created", ICON_INFO)
        else:
            # We didn't get an input file so generate an example and exit.

            # Create Example Input CSV file
            # Extract the script name from the full script path.
            script_name = crt.ScriptFullName.split(os.path.sep)[-1]

            # Create an example input filename by replacing .py in script
            # name with .csv
            example_file = os.path.normpath(
                os.path.join(
                    script_dir, script_name.replace(".py", ".csv")
                )
            )

            # Write out example
            with open(example_file, 'wb') as ex_file:
                exWriter = csv.writer(ex_file)
                exWriter.writerow(
                    ['session_name', 'hostname', 'protocol', 'folder']
                )
                exWriter.writerow(
                    ['switch1', '10.10.10.10', 'SSH2',
                     'Customer1/Site1/Building1/IDF1']
                )
                exWriter.writerow(
                    ['switch2', '10.10.20.10', 'SSH2',
                     'Customer1/Site1/Building1/IDF2']
                )
                exWriter.writerow(
                    ['router1', '10.10.10.1', 'SSH2',
                     'Customer1/Site1/Building1/IDF1']
                )

            # Show where example file was created
            setting_msg = (
                "No input file selected\n"
                "Example Import file, {0}, created in directory:\n{1}\n\n"
            ).format(example_file, script_dir)
            crt.Dialog.MessageBox(setting_msg,
                                  "Example Input Created",
                                  ICON_INFO)

if __name__ == "__builtin__":
    main()
