# $language = "python"
# $interface = "1.0"

# ################################################   SCRIPT INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# This script will capture the ARP table of the attached device and output the results as a CSV file.  While this
# script can be used to capture the ARP table, the primary purpose is to create the ARP associations that the
# "connected_ip.py" script can use to map which MAC and IP addresses are connected to each device.
#

# ################################################  SCRIPT SETTING  ###################################################
#
# Global settings that affect all scripts (output directory, date format, etc) is stored in the "global_settings.json"
# file in the "settings" directory.
#
# If any local settings are used for this script, they will be stored in the same settings folder, with the same name
# as the script that uses them, except ending with ".json".
#
# All settings can be manually modified in JSON format (the same syntax as Python lists and dictionaries). Be aware of
# required commas between items, or else options are likely to get run together and break the script.
#
# **IMPORTANT**  All paths saved in .json files must contain either forward slashes (/home/jcaesar) or
# DOUBLE back-slashes (C:\\Users\\Jamie).   Single backslashes will be considered part of a control character and will
# cause an error on loading.
#


# ################################################     IMPORTS      ###################################################
import os
import sys

# If the "crt" object exists, this is being run from SecureCRT.  Get script directory so we can add it to the
# PYTHONPATH, which is needed to import our custom modules.
if 'crt' in globals():
    script_dir, script_name = os.path.split(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
else:
    script_dir, script_name = os.path.split(os.path.realpath(__file__))
os.chdir(script_dir)

# Now we can import our custom modules
import securecrt_tools.sessions as sessions
import securecrt_tools.settings as settings
import securecrt_tools.utilities as utils


# ################################################  LOAD SETTINGS   ###################################################

session_set_filename = os.path.join(script_dir, "settings", settings.global_settings_filename)
session_settings = settings.SettingsImporter(session_set_filename, settings.global_defs)


# ################################################     SCRIPT       ###################################################

def script_main(session):
    supported_os = ["IOS", "NXOS"]
    if session.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Exiting program.".format(session.os))
        session.message_box("{0} is not a supported OS for this script.".format(session.os), "Unsupported OS",
                            options=sessions.ICON_STOP)
        return

    selected_vrf = session.prompt_window("Enter the VRF name.\n(Leave blank for default VRF)")
    if selected_vrf == "":
        selected_vrf = None
    logger.debug("Set VRF to '{0}'".format(selected_vrf))

    if session.os == "IOS":
        send_cmd = "show ip arp"
        template_file = "textfsm-templates/cisco_ios_show_ip_arp.template"
    else:
        send_cmd = "show ip arp detail"
        template_file = "textfsm-templates/cisco_nxos_show_ip_arp_detail.template"

    logger.debug("Command set to '{0}'".format(send_cmd))

    if selected_vrf:
        send_cmd = send_cmd + " vrf {0}".format(selected_vrf)
        session.hostname = session.hostname + "-VRF-{0}".format(selected_vrf)
        logger.debug("Updated hostname to: '{0}'".format(session.hostname))

    raw_arp = session.get_command_output(send_cmd)

    logger.debug("Using template: '{0}'".format(template_file))

    fsm_results = utils.textfsm_parse_to_list(raw_arp, template_file, add_header=True)

    output_filename = session.create_output_filename("arp", ext=".csv")
    utils.list_of_lists_to_csv(fsm_results, output_filename)

    # Clean up before closing session
    session.end()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, create our session object using the "crt" object provided by SecureCRT
if __name__ == "__builtin__":
    # Create a session object for this execution of the script and pass it to our main() function
    crt_session = sessions.CRTSession(crt, session_settings)
    if session_settings.get_setting('debug'):
        import logging
        logger = logging.getLogger("securecrt")
    script_main(crt_session)

# Else, if this script is run directly then create a session object without the SecureCRT API (crt object)  This would
# be done for debugging purposes (running the script outside of SecureCRT and feeding it the output it failed on)
elif __name__ == "__main__":
    direct_session = sessions.DirectSession(os.path.realpath(__file__), session_settings)
    if session_settings.get_setting('debug'):
        import logging
        logger = logging.getLogger("securecrt")
    script_main(direct_session)