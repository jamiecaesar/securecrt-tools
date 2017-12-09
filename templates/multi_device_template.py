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
from securecrt_tools import utilities
# Import message box constants names for use specifying the design of message boxes
from securecrt_tools.message_box_const import *

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(script):
    """
    | MULTIPLE device script
    | Author: XXXXXXXX
    | Email: XXXXXXX@domain.com

    PUT A DESCRIPTION OF THIS SCRIPT HERE.  WHAT IT DOES, ETC.
    This script assumes it will be run against a connected device.

    :param script: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type script: scripts.Script
    """
    # Create logger instance so we can write debug messages (if debug mode setting is enabled in settings).
    logger = logging.getLogger("securecrt")
    logger.debug("Starting execution of {}".format(script_name))

    session = script.get_script_tab()

    # If this is launched on an active tab, disconnect before continuing.
    logger.debug("<M_SCRIPT> Checking if current tab is connected.")
    if session.is_connected():
        logger.debug("<M_SCRIPT> Existing tab connected.  Stopping execution.")
        raise scripts.ScriptError("This script must be launched in a not-connected tab.")

    # Load a device list
    device_list = script.import_device_list()
    if not device_list:
        return

    check_mode = True
    # ##########################################  START CHECK MODE SECTION  ############################################
    # Ask if this should be a test run (generate configs only) or full run (push updates to devices)
    # Comment out or remove the entire CHECK MODE SECTION if you don't want to prompt for check mode
    check_mode_message = "Do you want to run this script in check mode? (Only generate configs)\n" \
                         "\n" \
                         "Yes = Connect to device and write change scripts to a file ONLY\n" \
                         "No = Connect to device and PUSH configuration changes"
    message_box_design = ICON_QUESTION | BUTTON_YESNOCANCEL
    logger.debug("Prompting the user to run in check mode.")
    result = script.message_box(check_mode_message, "Run in Check Mode?", message_box_design)
    if result == IDYES:
        logger.debug("<M_SCRIPT> Received 'True' for Check Mode.")
        check_mode = True
    elif result == IDNO:
        logger.debug("<M_SCRIPT> Received 'False' for Check Mode.")
        check_mode = False
    else:
        return
    # ###########################################  END CHECK MODE SECTION  #############################################

    jumpbox = None
    # ###########################################  START JUMP BOX SECTION  #############################################
    # Check if we need to use a jump box, and if so, prompt for the required values.
    # Delete/Comment out the entire JUMP BOX SECTION if you don't want to prompt for a jump box
    jump_connected = False
    j_username = None
    j_password = None
    j_ending = None
    need_jumpbox = script.message_box("Are these devices access through a jump box?", "Jump Box?",
                                      options=ICON_QUESTION | BUTTON_YESNO)
    if need_jumpbox == IDYES:
        logger.debug("<M_SCRIPT> User selected to use a jump box.  Prompting for information.")
        jumpbox = script.prompt_window("Enter the Hostname of IP of the jump box.")
        if jumpbox:
            j_username = script.prompt_window("Enter the USERNAME for {}".format(jumpbox))
            if j_username:
                j_password = script.prompt_window("Enter the PASSWORD for {}".format(j_username), hide_input=True)
                if j_password:
                    j_ending = script.prompt_window("Enter the last character of the jumpbox CLI prompt")
                    if j_ending:
                        session.connect_ssh(jumpbox, j_username, j_password, prompt_endings=[j_ending])
                        jump_connected = True

    # #############################################  END JUMP BOX SECTION  #############################################

    # Create a filename to keep track of our connection logs, if we have failures.  Use script name without extension
    failed_log = session.create_output_filename("{}-LOG".format(script_name.split(".")[0]), include_hostname=False)

    # #########################################  START DEVICE CONNECT LOOP  ############################################

    for device in device_list:
        hostname = device['hostname']
        protocol = device['protocol']
        username = device['username']
        password = device['password']
        enable = device['enable']

        if jumpbox:
            if "ssh" in protocol.lower():
                try:
                    if not jump_connected:
                        session.connect_ssh(jumpbox, j_username, j_password, prompt_endings=[j_ending])
                        jump_connected = True
                    session.ssh_via_jump(hostname, username, password)
                    per_device_work(session, check_mode, enable)
                    session.disconnect_via_jump()
                except (sessions.ConnectError, sessions.InteractionError) as e:
                    error_msg = e.message
                    with open(failed_log, 'a') as logfile:
                        logfile.write("Connect to {} failed: {}\n".format(hostname, error_msg))
                    session.disconnect()
                    jump_connected = False
            elif protocol.lower() == "telnet":
                try:
                    if not jump_connected:
                        session.connect_ssh(jumpbox, j_username, j_password, prompt_endings=[j_ending])
                        jump_connected = True
                    session.telnet_via_jump(hostname, username, password)
                    per_device_work(session, check_mode, enable)
                    session.disconnect_via_jump()
                except (sessions.ConnectError, sessions.InteractionError) as e:
                    with open(failed_log, 'a') as logfile:
                        logfile.write("Connect to {} failed: {}\n".format(hostname, e.message))
                    session.disconnect()
                    jump_connected = False
        else:
            try:
                session.connect(hostname, username, password, protocol=protocol)
                per_device_work(session, check_mode, enable)
                session.disconnect()
            except sessions.ConnectError as e:
                with open(failed_log, 'a') as logfile:
                    logfile.write("Connect to {} failed: {}\n".format(hostname, e.message))
            except sessions.InteractionError as e:
                with open(failed_log, 'a') as logfile:
                    logfile.write("Failure on {}: {}\n".format(hostname, e.message))

    # If we are still connected to our jump box, disconnect.
    if jump_connected:
        session.disconnect()

    # ##########################################  END DEVICE CONNECT LOOP  #############################################


def per_device_work(session, check_mode, enable_pass):
    """
    This function should contain the logic that should be executed on each device.  It receives the values from
    prompting the user in the main script logic (check mode and enable password), and is called on every device that is
    connected to as the script loops through the device list in the script_main() function.

    This function is called immediately after making a connection to a device and should only be the logic needed to
    interact with the device.  Opening and closing the connection is handled as the main script loops through devices
    in the list.  In general, that means it should start with "start_cisco_session()" and end with "end_cisco_session()"
    """
    session.start_cisco_session()
    #
    # Your Code Here
    #
    session.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_script = scripts.CRTScript(crt)
    script_main(crt_script)
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_script = scripts.DirectScript(os.path.realpath(__file__))
    script_main(direct_script)
    logging.shutdown()
