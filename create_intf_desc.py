# $language = "python"
# $interface = "1.0"

# ################################################   SCRIPT INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# This script will grab the detailed CDP information from a Cisco IOS or NX-OS device and output a text file containing
# the configuration scripts to label all the interfaces found in the CDP table.
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
import logging

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
                          '_strip_domains_comment': "A list of strings to remove if found in the device ID of CDP "
                                                    "output.  Configurable due to '.' being a valid hostname "
                                                    "character and doesn't always signify a component of FQDN.",
                          'strip_domains': [".cisco.com", ".Cisco.com"]
                          }
local_importer = settings.SettingsImporter(local_set_filename, local_settings_default)
local_settings = local_importer.get_settings_dict()

# Set logger variable -- this won't be used unless debug setting is True
logger = logging.getLogger("securecrt")

# ################################################     SCRIPT       ###################################################

def extract_cdp_data(cdp_table):
    """
    Extract remote host and interface for each local interface in the CDP table

    :param cdp_table:  The TextFSM output for CDP neighbor detail
    :return:  A dictionary for each local interface with corresponding remote host and interface.
    """
    cdp_data = {}
    found_intfs = set()

    # Loop through all entry, excluding header row
    for entry in cdp_table[1:]:
        local_intf = entry[0]
        device_id = entry[1]
        system_name = entry[2]
        remote_intf = entry[3]
        if system_name == "":
            system_name = utils.extract_system_name(device_id)

        # 7Ks can give multiple CDP entries when VDCs share the mgmt0 port.  If duplicate name is found, remove it
        if local_intf in found_intfs:
            # Remove from our description list
            cdp_data.pop(system_name, None)
        else:
            cdp_data[local_intf] = (system_name, remote_intf)
            found_intfs.add(local_intf)

    return cdp_data


def add_port_channels(desc_data, pc_data):
    for entry in pc_data:
        po_name = entry[0]
        intf_list = entry[4]
        neighbor_set = set()
        # For each index in the intf_list
        for intf in intf_list:
            long_name = utils.long_int_name(intf)
            if long_name in desc_data:
                neighbor_set.add(desc_data[long_name][0])
        if len(neighbor_set) > 0:
            desc_data[po_name] = list(neighbor_set)


def script_main(session):
    send_cmd = "show cdp neighbors detail"
    logger.debug("Command set to '{0}'".format(send_cmd))

    raw_cdp = session.get_command_output(send_cmd)

    template_file = "textfsm-templates/cisco_os_show_cdp_neigh_det.template"
    logger.debug("Using template: '{0}'".format(template_file))

    fsm_results = utils.textfsm_parse_to_list(raw_cdp, template_file, add_header=True)

    # Since "System Name" is a newer NXOS feature -- try to extract it from the device ID when its empty.
    for entry in fsm_results:
        # entry[2] is system name, entry[1] is device ID
        if entry[2] == "":
            entry[2] = utils.extract_system_name(entry[1], strip_list=local_settings['strip_domains'])

    description_data = extract_cdp_data(fsm_results)

    # Capture port-channel output
    if session.os == "NX-OS":
        raw_pc_output = session.get_command_output("show port-channel summary")
        pc_template = "textfsm-templates/cisco_nxos_show_portchannel_summary.template"
        pc_table = utils.textfsm_parse_to_list(raw_pc_output, pc_template, add_header=True)
        add_port_channels(description_data, pc_table)
    elif session.os == "IOS":
        raw_pc_output = session.get_command_output("show etherchannel summary")
        pc_template = "textfsm-templates/cisco_ios_show_etherchannel_summary.template"
        pc_table = utils.textfsm_parse_to_list(raw_pc_output, pc_template, add_header=True)
        add_port_channels(description_data, pc_table)
    else:
        pass

    # This will contain our configuration commands as CDP neighbors are found.
    config_script = ""
    # Generate a string of config commands to apply interface descriptions
    intf_list = sorted(description_data.keys(), key=utils.human_sort_key)
    for interface in intf_list:
        config_script += "interface {}\n".format(interface)
        if "Po" in interface:
            neigh_list = description_data[interface]
            if len(neigh_list) == 1:
                config_script += "  description {}\n".format(neigh_list[0])
            if len(neigh_list) == 2:
                neigh_list = sorted(neigh_list, key=utils.human_sort_key)
                config_script += "  description vPC from {}, {}\n".format(neigh_list[0], neigh_list[1])
        else:
            config_script += "  description {}, {}\n".format(description_data[interface][0],
                                                             utils.short_int_name(description_data[interface][1]))

    output_filename = session.create_output_filename("intf-desc", include_date=False)
    with open(output_filename, 'wb') as output_file:
        output_file.write(config_script)

    # Clean up before closing session
    session.end()


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, create our session object using the "crt" object provided by SecureCRT
if __name__ == "__builtin__":
    # Create a session object for this execution of the script and pass it to our main() function
    crt_session = sessions.CRTSession(crt, session_settings)
    script_main(crt_session)

# Else, if this script is run directly then create a session object without the SecureCRT API (crt object)  This would
# be done for debugging purposes (running the script outside of SecureCRT and feeding it the output it failed on)
elif __name__ == "__main__":
    direct_session = sessions.DirectSession(os.path.realpath(__file__), session_settings)
    script_main(direct_session)