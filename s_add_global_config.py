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
from securecrt_tools import ipaddress
from securecrt_tools.message_box_const import *

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {0}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def add_commands(session, check_mode, commands_to_add):
    # If we are pushing commands to a real device, save our "Before" configuration.
    if not check_mode:
        before_filename = session.create_output_filename("1-show-run-BEFORE")
        session.write_output_to_file("show run", before_filename)

    if commands_to_add:
        if check_mode:
            # If in Check Mode, only generate config updates and write to a file.
            logger.debug("<ADD_GLOBAL_CONFIG> CHECK MODE: Generating config")
            command_string = ""
            command_string += "configure terminal\n"
            for command in commands_to_add:
                command_string += "{}\n".format(command.strip())
            command_string += "end\n"

            config_filename = session.create_output_filename("PROPOSED_CONFIG")
            with open(config_filename, 'w') as output_file:
                output_file.write(command_string)
        else:
            config_filename = session.create_output_filename("2-CONFIG_RESULTS")
            session.send_config_commands(commands_to_add, output_filename=config_filename)
            session.save()

            # Save our "After" configuration.
            after_filename = session.create_output_filename("3-show-run-AFTER")
            session.write_output_to_file("show run", after_filename)


def script_main(session):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will add global configuration commands to the connected device.  The commands sent will depend on the
    operating system of the connected device.  For example, IOS devices get the commands listed in the 'ios' section of
    the settings for this script.   If the device is running NX-OS, it will get the commands from the 'nxos' section of
    the settings, etc.

    This script will prompt you to run in "Check Mode", where the configuration changes the script would be pushed to
    the device are ONLY written to a file and NO CHANGES will be made to the device.  If you select "No" when prompted
    this script will push the configuration changes to the device. Also, when the changes are pushed to the device this
    script will save the running config before and after the changes are made, and will also output a log of the
    configuration session showing all the commands pushed.

    **Script Settings** (found in settings/settings.ini):

    * | **show_instructions** - When True, displays a pop-up upon launching the script
      | explaining where to modify the list of commands sent to devices.  This window also
      | prompts the user if they want to continue seeing this message. If not, the script
      | changes this setting to False.
    * | **ios** - A comma separated list of commands that will be sent to IOS devices.
    * | **ios-xr** - A comma separated list of commands that will be sent to IOS-XR devices.
    * | **nxos** - A comma separated list of commands that will be sent to NX-OS devices.
    * | **asa** - A comma separated list of commands that will be sent to ASA devices.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # ----------------------------------- GET VALUES FROM SETTINGS -----------------------------------

    settings_header = "add_global_config"
    # Display instructions message, unless settings prevent it
    show_instructions = script.settings.getboolean(settings_header, "show_instructions")
    if show_instructions:
        response = script.message_box("The list of commands sent to each device (per network OS) can be edited in the "
                                      "'settings/settings.ini' file in the main securecrt-tools directory.\nSee the "
                                      "documentation for this script ('docs/index.html') for more details.\n\n"
                                      "Do you want to stop seeing this message?",
                                      "Instructions", ICON_QUESTION + BUTTON_YESNO)
        if response == IDYES:
            script.settings.update(settings_header, "show_instructions", False)

    # ----------------------------------- PROMPT FOR CHECK-MODE -----------------------------------

    # Ask if this should be a test run (generate configs only) or full run (push updates to devices)
    check_mode_message = "THIS SCRIPT WILL MAKE CONFIG CHANGES ON THE REMOTE DEVICES!!!!!\n\n" \
                         "Do you want to run this script in check mode instead? (Only generate configs)\n" \
                         "\n" \
                         "Yes = Connect to device and write change scripts to a file only. NO CHANGES.\n" \
                         "No = Connect to device and PUSH CONFIGURATION CHANGES TO ALL DEVICES"
    logger.debug("<ADD_GLOBAL_CONFIG> Prompting the user to run in check mode.")
    result = script.message_box(check_mode_message, "Run in Check Mode?", ICON_QUESTION + BUTTON_YESNOCANCEL)
    if result == IDYES:
        check_mode = True
    elif result == IDNO:
        check_mode = False
    else:
        return

    # -----------------------------------  MAIN SCRIPT LOGIC  -----------------------------------

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    commands_to_add = script.settings.getlist(settings_header, session.os)
    logger.debug("<ADD_GLOBAL_CONFIG> Commands to send:\n{}".format(str(commands_to_add)))
    if commands_to_add:
        add_commands(session, check_mode, commands_to_add)
    else:
        logger.debug("<ADD_GLOBAL_CONFIG> No commands to send to {}, skipping device.\n".format(session.hostname))
        script.message_box("There are no commands for OS type: {}".format(session.os), "No Commands", ICON_STOP)

    # Return terminal parameters back to the original state.
    session.end_cisco_session()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    # Initialize script object
    crt_script = scripts.CRTScript(crt)
    # Get session object for the SecureCRT tab that the script was launched from.
    crt_session = crt_script.get_main_session()
    # Run script's main logic against our session
    try:
        script_main(crt_session)
    except Exception:
        crt_session.end_cisco_session()
        raise
    # Shutdown logging after
    logging.shutdown()

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    # Initialize script object
    direct_script = scripts.DebugScript(os.path.realpath(__file__))
    # Get a simulated session object to pass into the script.
    sim_session = direct_script.get_main_session()
    # Run script's main logic against our session
    script_main(sim_session)
    # Shutdown logging after
    logging.shutdown()
