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
from securecrt_tools import sessions

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(session):
    """
    This script will prompt the user for a command for a Cisco device and save the output into a file.
    The path where the file is saved is specified in settings.ini file.
    This script assumes that you are already connected to the device before running it.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Start session with device
    session.start_cisco_session()

    send_cmd = session.prompt_window("Enter the command to capture")
    logger.debug("Received command: '{0}'".format(send_cmd))

    if send_cmd == "":
        return

    # Generate filename used for output files.
    full_file_name = session.create_output_filename(send_cmd)

    # Get the output of our command and save it to the filename specified
    session.write_output_to_file(send_cmd, full_file_name)

    # Clean up before closing session
    session.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_session = sessions.CRTSession(crt)
    script_main(crt_session)

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_session = sessions.DirectSession(os.path.realpath(__file__))
    script_main(direct_session)
