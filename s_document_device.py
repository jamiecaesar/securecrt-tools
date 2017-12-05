# $language = "python"
# $interface = "1.0"

import os
import sys
import logging

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
    SINGLE device script
    Author: Jamie Caesar
    Email: jcaesar@presidio.com

    This script will grab the output for a list of commands from the connected device.  The list of commands is taken
    from the 'settings/settings.ini' file.  There is a separate list for each supported network operating system (IOS,
    NXOS and ASA).

    Script Settings (found in settings/settings.ini):
    folder_per_device - If True, Creates a folder for each device, based on the hostname, and saves all files inside
        that folder.  If False, it saves all the files directly into the output folder from the global settings.
    ios - The list of commands that will be run on IOS devices
    nxos - The list of commands that will be run on NXOS devices
    asa - The list of commands that will be run on ASA devices

    The outputs will be saved in a folder named after the hostname of the device, with each output file being saved
    inside that directory.

    :param script: A subclass of the sessions.Session object that represents this particular script session (either
                   SecureCRTSession or DirectSession)
    :type script: script_types.Script
    """
    # Create logger instance so we can write debug messages (if debug mode setting is enabled in settings).
    logger = logging.getLogger("securecrt")
    logger.debug("Starting execution of {}".format(script_name))

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    script.start_cisco_session()

    # Validate device is running a supported OS
    supported_os = ["IOS", "NXOS", "ASA"]
    if script.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Raising exception.".format(script.os))
        raise script_types.UnsupportedOSError("Remote device running unsupported OS: {0}.".format(script.os))

    command_list = script.settings.getlist(script_name, script.os)
    folder_per_device = script.settings.getboolean(script_name, "folder_per_device")

    if folder_per_device:
        output_dir = os.path.join(script.output_dir, script.hostname)
    else:
        output_dir = script.output_dir

    for command in command_list:
        # Generate filename used for output files.
        full_file_name = script.create_output_filename(command, include_hostname=not folder_per_device, base_dir=output_dir)
        # Get the output of our command and save it to the filename specified
        script.write_output_to_file(command, full_file_name)

    # Return terminal parameters back to the original state.
    script.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_script = script_types.CRTScript(crt)
    script_main(crt_script)

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_script = script_types.DirectScript(os.path.realpath(__file__))
    script_main(direct_script)