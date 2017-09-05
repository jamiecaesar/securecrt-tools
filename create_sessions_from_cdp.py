# $language = "python"
# $interface = "1.0"

# ################################################   SCRIPT INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# This script will grab the detailed CDP information from a Cisco IOS or NX-OS device and create SecureCRT sessions
# based on the information, making it easier to manually crawl through a new network.
#
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

local_set_filename = os.path.join(script_dir, "settings", script_name.replace(".py", ".json"))
local_settings_default = {'__version': "1.0",
                          '_session_path_comment': "session_path roots in the SecureCRT Sessions directory.  USE "
                                                   "FORWARD SLASHES OR DOUBLE-BACKSLASHES IN SESSION PATHS! SINGLE "
                                                   "BACKSLASHES WILL ERROR.",
                          'session_path': "_imports",
                          '_strip_domains_comment': "A list of strings to remove if found in the device ID of CDP "
                                                    "output",
                          'strip_domains': [".cisco.com", ".Cisco.com"]
                          }
local_importer = settings.SettingsImporter(local_set_filename, local_settings_default)
local_settings = local_importer.get_settings_dict()


# ################################################     SCRIPT       ###################################################

def create_sessions_from_cdp(session, cdp_list, settings):
    count = 0
    skipped = 0
    created = set()
    for device in cdp_list:
        # Extract hostname and IP to create session
        system_name = device[2]

        # If we couldn't get a System name, use the device ID
        if system_name == "":
            system_name = device[1]

        if system_name in created:
            logger.debug("Skipping {0} because it is a duplicate.".format(system_name))
            skipped += 1
            continue

        mgmt_ip = device[7]
        if mgmt_ip == "":
            if device[4] == "":
                # If no mgmt IP or interface IP, skip device.
                skipped += 1
                logger.debug("Skipping {0} because cannot find IP in CDP data.".format(system_name))
                continue
            else:
                mgmt_ip = device[4]
                logger.debug("Using interface IP ({0}) for {1}.".format(mgmt_ip, system_name))
        else:
            logger.debug("Using management IP ({0}) for {1}.".format(mgmt_ip, system_name))


        # Create a new session from the default information.
        session.create_new_saved_session(system_name, mgmt_ip, folder=settings['session_path'])
        # Track the names of the hosts we've made already
        logger.debug("Created session for {0}.".format(system_name))
        created.add(system_name)
        count += 1

    logger.debug("Finished creating {0} sessions, and skipped {1}".format(count, skipped))
    return count, skipped


def script_main(session):
    supported_os = ["IOS", "NXOS"]
    if session.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Exiting program.".format(session.os))
        session.message_box("{0} is not a supported OS for this script.".format(session.os), "Unsupported OS",
                            options=sessions.ICON_STOP)
        return

    send_cmd = "show cdp neighbors detail"

    raw_cdp = session.get_command_output(send_cmd)

    template_file = "textfsm-templates/cisco_os_show_cdp_neigh_det.template"

    cdp_table = utils.textfsm_parse_to_list(raw_cdp, template_file)

    # Since "System Name" is a newer NXOS feature -- try to extract it from the device ID when its empty.
    for entry in cdp_table:
        # entry[2] is system name, entry[1] is device ID
        if entry[2] == "":
            entry[2] = utils.extract_system_name(entry[1], strip_list=local_settings['strip_domains'])

    num_created, num_skipped = create_sessions_from_cdp(session, cdp_table, local_settings)

    setting_msg = "{0} sessions created in the directory '{1}' under Sessions\n\n{2} sessions skipped (no IP or " \
                  "duplicate)".format(num_created, local_settings['session_path'], num_skipped)
    session.message_box(setting_msg, "Sessions Created", sessions.ICON_INFO)

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