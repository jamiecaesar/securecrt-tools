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
from securecrt_tools import utilities


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(session):
    """
    Author: XXXXXXXX
    Email: XXXXXXX@domain.com

    PUT A DESCRIPTION OF THIS SCRIPT HERE.  WHAT IT DOES, ETC.
    This script assumes it will be run against a connected device.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type session: sessions.Session
    """
    # Create logger instance so we can write debug messages (if debug mode setting is enabled in settings).
    logger = logging.getLogger("securecrt")
    logger.debug("Starting execution of {}".format(script_name))

    # Start session with device (This assumes we are already connected to a device)
    session.start_cisco_session()
    #
    # PUT YOUR CODE HERE
    #
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