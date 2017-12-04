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
    Author: Jamie Caesar
    Email: jcaesar@presidio.com

    This script will grab the detailed CDP information from a Cisco IOS or NX-OS device and port-channel information and
    generate the commands to update interface descriptions.  The user will be prompted to run in "Check Mode" which will
    write the configuration changes to a file (for verification or later manual application).  If not, then the script
    will push the configuration commands to the device and save the configuration.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type session: sessions.Session
    """
    # Create logger instance so we can write debug messages (if debug mode setting is enabled in settings).
    logger = logging.getLogger("securecrt")
    logger.debug("Starting execution of {}".format(script_name))

    # Start session with device (This assumes we are already connected to a device)
    session.start_cisco_session()

    # Validate device is running a supported OS
    supported_os = ["IOS", "NXOS"]
    if session.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Raising exception.".format(session.os))
        raise sessions.UnsupportedOSError("Remote device running unsupported OS: {0}.".format(session.os))

    # Ask if this should be a test run (generate configs only) or full run (push updates to devices)
    check_mode_message = "Do you want to run this script in check mode? (Only generate configs)\n" \
                         "\n" \
                         "Yes = Connect to device and write change scripts to a file ONLY\n" \
                         "No = Connect to device and PUSH configuration changes"
    message_box_design = sessions.ICON_QUESTION | sessions.BUTTON_YESNOCANCEL
    logger.debug("Prompting the user to run in check mode.")
    result = session.message_box(check_mode_message, "Run in Check Mode?", message_box_design)
    if result == sessions.IDYES:
        check_mode = True
    elif result == sessions.IDNO:
        check_mode = False
    else:
        return

    # Get CDP Data
    raw_cdp = session.get_command_output("show cdp neighbors detail")

    # Process CDP Data with TextFSM
    template_file = session.get_template("cisco_os_show_cdp_neigh_det.template")
    fsm_results = utilities.textfsm_parse_to_list(raw_cdp, template_file, add_header=True)

    # Get domain names to strip from device IDs from settings file
    strip_list = session.settings.getlist(script_name, "strip_domains")

    # Since "System Name" is a newer NXOS feature -- try to extract it from the device ID when its empty.
    for entry in fsm_results:
        # entry[2] is system name, entry[1] is device ID
        if entry[2] == "":
            entry[2] = utilities.extract_system_name(entry[1], strip_list=strip_list)

    # Get Remote name, local and remote interface info to build descriptions.
    description_data = extract_cdp_data(fsm_results)

    # Capture port-channel output and add details to our description information
    if session.os == "NXOS":
        raw_pc_output = session.get_command_output("show port-channel summary")
        pc_template = session.get_template("cisco_nxos_show_portchannel_summary.template")
        pc_table = utilities.textfsm_parse_to_list(raw_pc_output, pc_template, add_header=True)
        add_port_channels(description_data, pc_table)
    else:
        raw_pc_output = session.get_command_output("show etherchannel summary")
        pc_template = session.get_template("cisco_ios_show_etherchannel_summary.template")
        pc_table = utilities.textfsm_parse_to_list(raw_pc_output, pc_template, add_header=True)
        add_port_channels(description_data, pc_table)

    # Generate a list of configuration commands
    config_commands = []
    intf_list = sorted(description_data.keys(), key=utilities.human_sort_key)
    for interface in intf_list:
        config_commands.append("interface {}".format(interface))
        if "Po" in interface:
                neigh_list = description_data[interface]
                if len(neigh_list) == 1:
                    config_commands.append(" description {}".format(neigh_list[0]))
                if len(neigh_list) == 2:
                    neigh_list = sorted(neigh_list, key=utilities.human_sort_key)
                    config_commands.append(" description vPC from {}, {}".format(neigh_list[0], neigh_list[1]))
        else:
            remote_host = description_data[interface][0]
            remote_intf = utilities.short_int_name(description_data[interface][1])
            config_commands.append(" description {}, {}".format(remote_host, remote_intf))

    # If in check-mode, generate configuration and write it to a file, otherwise push the config to the device.
    if check_mode:
        output_filename = session.create_output_filename("intf-desc", include_date=False)
        with open(output_filename, 'wb') as output_file:
            for command in config_commands:
                output_file.write("{}\n".format(command))
    else:
        # Check settings to see if we prefer to save backups before/after applying changes
        take_backups = session.settings.getboolean(script_name, "take_backups")
        if take_backups:
            # Back up running config prior to changes
            before_filename = session.create_output_filename("1-show-run-BEFORE")
            session.write_output_to_file("show run", before_filename)
            # Push configuration, capturing the configure terminal log
            output_filename = before_filename.replace("1-show-run-BEFORE", "2-CONFIG-RESULTS")
            session.send_config_commands(config_commands, output_filename)
            # Back up configuration after changes are applied
            after_filename = before_filename.replace("1-show-run-BEFORE", "3-show-run-AFTER")
            session.write_output_to_file("show run", after_filename)
        else:
            # Push configuration, capturing the configure terminal log
            output_filename = session.create_output_filename("CONFIG-RESULTS")
            session.send_config_commands(config_commands, output_filename)

        # Save configuration
        session.save()

    # Clean up before closing session
    session.end_cisco_session()


def extract_cdp_data(cdp_table):
    """
    Extract only remote host and interface for each local interface in the CDP table

    :param cdp_table: The TextFSM output for CDP neighbor detail
    :type cdp_table: list of list

    :return: A dictionary for each local interface with corresponding remote host and interface.
    :rtype: dict
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
            system_name = utilities.extract_system_name(device_id)

        # 7Ks can give multiple CDP entries when VDCs share the mgmt0 port.  If duplicate name is found, remove it
        if local_intf in found_intfs:
            # Remove from our description list
            cdp_data.pop(system_name, None)
        else:
            cdp_data[local_intf] = (system_name, remote_intf)
            found_intfs.add(local_intf)

    return cdp_data


def add_port_channels(desc_data, pc_data):
    """
    Adds port-channel information to our CDP data so that we can also put descriptions on port-channel interfaces that
    have members found in the CDP table.

    :param desc_data: Our CDP description data that needs to be updated
    :type desc_data:
    :param pc_data:
    :type: pc_data:
    """
    for entry in pc_data:
        po_name = entry[0]
        intf_list = entry[4]
        neighbor_set = set()

        # For each index in the intf_list
        for intf in intf_list:
            long_name = utilities.long_int_name(intf)
            if long_name in desc_data:
                neighbor_set.add(desc_data[long_name][0])
        if len(neighbor_set) > 0:
            desc_data[po_name] = list(neighbor_set)





# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_session = sessions.CRTSession(crt)
    script_main(crt_session)

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_session = sessions.DirectSession(os.path.realpath(__file__))
    script_main(direct_session)
