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
from securecrt_tools import scripts
from securecrt_tools import sessions
import s_cdp_to_csv

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(script):
    """
    | MULTIPLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will grab the detailed CDP information from each Cisco IOS or NX-OS device in the provided device list
    CSV file and export each to a CSV file containing the important information, such as Remote Device hostname, model
    and IP information, in addition to the local and remote interfaces that connect the devices.

    :param script: A subclass of the scripts.Script object that represents the execution of this particular script
                   (either CRTScript or DirectScript)
    :type script: scripts.Script
    """
    session = script.get_main_session()

    # If this is launched on an active tab, disconnect before continuing.
    logger.debug("<M_CDP_TO_CSV> Checking if current tab is connected.")
    if session.is_connected():
        logger.debug("<M_CDP_TO_CSV> Existing tab connected.  Stopping execution.")
        raise scripts.ScriptError("This script must be launched in a not-connected tab.")

    # Load a device list
    device_list = script.import_device_list()
    if not device_list:
        return

    # Check settings if we should use a proxy/jumpbox
    use_proxy = script.settings.getboolean("Global", "use_proxy")
    default_proxy_session = script.settings.get("Global", "proxy_session")

    # ########################################  START DEVICE CONNECT LOOP  ###########################################

    # Create a filename to keep track of our connection logs, if we have failures.  Use script name without extension
    failed_log = session.create_output_filename("{0}-LOG".format(script_name.split(".")[0]), include_hostname=False)

    for device in device_list:
        hostname = device['Hostname']
        protocol = device['Protocol']
        username = device['Username']
        password = device['Password']
        enable = device['Enable']
        try:
            proxy = device['Proxy Session']
        except KeyError:
            proxy = None

        if not proxy and use_proxy:
            proxy = default_proxy_session

        logger.debug("<M_CDP_TO_CSV> Connecting to {0}".format(hostname))
        try:
            session.connect(hostname, username, password, protocol=protocol)
            per_device_work(session, enable)
            session.disconnect()
        except sessions.ConnectError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("Connect to {0} failed: {1}\n".format(hostname, e.message))
        except sessions.InteractionError as e:
            with open(failed_log, 'a') as logfile:
                logfile.write("Failure on {0}: {1}\n".format(hostname, e.message))

    # ##########################################  END DEVICE CONNECT LOOP  #############################################


def per_device_work(session, enable_pass):
    """
    This function contains the code that should be executed on each device that this script connects to.  It is called
    after establishing a connection to each device in the loop above.

    You can either put your own code here, or if there is a single-device version of a script that performs the correct
    task, it can be imported and called here, essentially making this script connect to all the devices in the chosen
    CSV file and then running a single-device script on each of them.
    """
    s_cdp_to_csv.script_main(session)


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Run script's main logic against the script object
    script_main(crt_script)
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Run script's main logic against the script object
    script_main(direct_script)
    # Shutdown logging after
    logging.shutdown()