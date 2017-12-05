# $language = "python"
# $interface = "1.0"

import os
import sys
import logging
import csv

# Add script directory to the PYTHONPATH so we can import our modules (only if run from SecureCRT)
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))

# Now we can import our custom modules
from securecrt_tools import script_types
from securecrt_tools import utilities

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(script):
    """
    Author: Michael Ethridge
    Email: michael@methridge.com

    This script will import a list of sessions to create in SecureCRT from a CSV file.  It does not connect to any
    devices.

    :param script: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type script: script_types.Script
    """
    # Create logger instance so we can write debug messages (if debug mode setting is enabled in settings).
    logger = logging.getLogger("securecrt")
    logger.debug("Starting execution of {}".format(script_name))

    # Get input CSV, must contain Session Name and IP.  Can also have
    # Protocol and folder
    sessions_csv = ""
    sessions_csv = script.file_open_dialog("Please select your CSV Import file", "Open", sessions_csv,
                                           "CSV Files (*.csv)|*.csv|")

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
                script.create_new_saved_session(row['session_name'], row['hostname'], row['protocol'], row['folder'])
                count += 1

        # Display summary of created / skipped sessions
        setting_msg = "{} sessions created\n{} sessions skipped (no Hostname / IP)".format(count, skipped)
        script.message_box(setting_msg, "Sessions Created", script_types.ICON_INFO)
    else:
        # We didn't get an input file so ask to generate an example and exit.
        result = script.message_box("Do you want to generate an example CSV file?", "Generate CSV",
                           script_types.ICON_QUESTION|script_types.BUTTON_YESNO)
        if result == script_types.IDNO:
            return
        else:
            # Create an example input filename by replacing .py in script
            # name with .csv
            example_file = os.path.normpath(os.path.join(script_dir, script_name.replace(".py", ".csv")))

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
                "Example Import file, {0}, created in directory:\n{1}\n\n").format(example_file, script_dir)
            script.message_box(setting_msg, "Example Input Created", script_types.ICON_INFO)


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_script = script_types.CRTScript(crt)
    script_main(crt_script)

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_script = script_types.DirectScript(os.path.realpath(__file__))
    script_main(direct_script)