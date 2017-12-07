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
# Import message box constants names for use specifying the design of message boxes
from securecrt_tools.message_box_const import *

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(script, prompt_checkmode=True, check_mode=True, enable_pass=None):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will grab the detailed CDP information from a Cisco IOS or NX-OS device and port-channel information and
    generate the commands to update interface descriptions.  The user will be prompted to run in "Check Mode" which will
    write the configuration changes to a file (for verification or later manual application).  If not, then the script
    will push the configuration commands to the device and save the configuration.

    Local Settings:
    "strip_domains" -  A list of domain names that will be stripped away if found in the CDP remote device name.
    "take_backups" - If set to True, the script will save a copy of the running config before and after making changes.
    "rollback_file" - If set to True, the script will generate a rollback configuration script and save it to a file.

    :param script: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type script: script_types.Script
    :param prompt_checkmode: A boolean that specifies if we should prompt the user to find out if we should run in
        "check mode".  We would make this False if we were using this function in a multi-device script, so that the
        process can run continually without prompting the user at each device.
    :type prompt_checkmode: bool
    :param check_mode: A boolean to specify whether we should run in "check mode" (Generate what the script would do
        only -- does not push config), or not (Pushes the changes to the device).   The default is True for safety
        reasons, and this option will be overwritten unless prompt_checkmode is False.
    :type check_mode: bool
    :param enable_pass: The enable password for the device.  Will be passed to start_cisco_session method if available.
    :type enable_pass: str
    """
    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    script.start_cisco_session(enable_pass=enable_pass)

    # Validate device is running a supported OS
    supported_os = ["IOS", "NXOS"]
    if script.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Raising exception.".format(script.os))
        raise script_types.UnsupportedOSError("Remote device running unsupported OS: {0}.".format(script.os))

    if prompt_checkmode:
        # Ask if this should be a test run (generate configs only) or full run (push updates to devices)
        check_mode_message = "Do you want to run this script in check mode? (Only generate configs)\n" \
                             "\n" \
                             "Yes = Connect to device and write change scripts to a file ONLY\n" \
                             "No = Connect to device and PUSH configuration changes"
        message_box_design = ICON_QUESTION | BUTTON_YESNOCANCEL
        logger.debug("Prompting the user to run in check mode.")
        result = script.message_box(check_mode_message, "Run in Check Mode?", message_box_design)
        if result == IDYES:
            check_mode = True
        elif result == IDNO:
            check_mode = False
        else:
            return

    # Get existing descriptions, so we don't push commands that would not change the description.
    ex_desc_lookup = get_desc_table(script)

    # Get CDP Data
    raw_cdp = script.get_command_output("show cdp neighbors detail")

    # Process CDP Data with TextFSM
    template_file = script.get_template("cisco_os_show_cdp_neigh_det.template")
    fsm_results = utilities.textfsm_parse_to_list(raw_cdp, template_file, add_header=True)

    # Get domain names to strip from device IDs from settings file
    strip_list = script.settings.getlist("update_interface_desc", "strip_domains")

    # Since "System Name" is a newer NXOS feature -- try to extract it from the device ID when its empty.
    for entry in fsm_results:
        # entry[2] is system name, entry[1] is device ID. Localhost is a corner case for ESX hosts, where DNS name is
        # in DeviceID, but localhost is in System Name
        if entry[2] == "" or entry[2] == "localhost":
            entry[2] = utilities.extract_system_name(entry[1], strip_list=strip_list)

    # Get Remote name, local and remote interface info to build descriptions.
    description_data = extract_cdp_data(fsm_results)

    # Capture port-channel output and add details to our description information
    if script.os == "NXOS":
        raw_pc_output = script.get_command_output("show port-channel summary")
        pc_template = script.get_template("cisco_nxos_show_portchannel_summary.template")
        pc_table = utilities.textfsm_parse_to_list(raw_pc_output, pc_template, add_header=True)
        add_port_channels(description_data, pc_table)
    else:
        raw_pc_output = script.get_command_output("show etherchannel summary")
        pc_template = script.get_template("cisco_ios_show_etherchannel_summary.template")
        pc_table = utilities.textfsm_parse_to_list(raw_pc_output, pc_template, add_header=True)
        add_port_channels(description_data, pc_table)

    # Create a list to append configuration commands and rollback commands
    config_commands = []
    rollback = []

     # Get an alphabetically sorted list of interfaces
    intf_list = sorted(description_data.keys(), key=utilities.human_sort_key)

    # Generate a list of configuration commands (and rollback if necessary)
    for interface in intf_list:
        # Get existing description
        try:
            existing_desc = ex_desc_lookup[interface]
        except KeyError:
            existing_desc = ""

        # If a port-channel only use hostname in description
        if "Po" in interface:
                neigh_list = description_data[interface]
                # If there is only 1 neighbor, use that
                if len(neigh_list) == 1:
                    new_desc = neigh_list[0]
                # If there are 2 neighbors, assume a vPC and label appropriately
                if len(neigh_list) == 2:
                    neigh_list = sorted(neigh_list, key=utilities.human_sort_key)
                    new_desc = "vPC: {}, {}".format(neigh_list[0], neigh_list[1])
                # Only update description if we will be making a change
                if new_desc != existing_desc:
                    config_commands.append("interface {}".format(interface))
                    config_commands.append(" description {}".format(new_desc))
                    rollback.append("interface {}".format(interface))
                    if not existing_desc:
                        rollback.append(" no description")
                    else:
                        rollback.append(" description {}".format(existing_desc))

        # For other interfaces, use remote hostname and interface
        else:
            remote_host = description_data[interface][0]
            remote_intf = utilities.short_int_name(description_data[interface][1])
            new_desc = "{} {}".format(remote_host, remote_intf)
            # Only update description if we will be making a change
            if new_desc != existing_desc:
                config_commands.append("interface {}".format(interface))
                config_commands.append(" description {}".format(new_desc))
                rollback.append("interface {}".format(interface))
                if not existing_desc:
                    rollback.append(" no description")
                else:
                    rollback.append(" description {}".format(existing_desc))

    # If in check-mode, generate configuration and write it to a file, otherwise push the config to the device.
    if config_commands:
        if check_mode:
            output_filename = script.create_output_filename("intf-desc", include_date=False)
            with open(output_filename, 'wb') as output_file:
                for command in config_commands:
                    output_file.write("{}\n".format(command))
            rollback_filename = script.create_output_filename("rollback", include_date=False)
        else:
            # Check settings to see if we prefer to save backups before/after applying changes
            take_backups = script.settings.getboolean("update_interface_desc", "take_backups")
            if take_backups:
                # Back up running config prior to changes
                before_filename = script.create_output_filename("1-show-run-BEFORE")
                script.write_output_to_file("show run", before_filename)
                # Push configuration, capturing the configure terminal log
                output_filename = script.create_output_filename("2-CONFIG-RESULTS")
                script.send_config_commands(config_commands, output_filename)
                # Back up configuration after changes are applied
                after_filename = script.create_output_filename("3-show-run-AFTER")
                script.write_output_to_file("show run", after_filename)
                # Set Rollback filename, in case this option is used
                rollback_filename = script.create_output_filename("4-ROLLBACK")
            else:
                # Push configuration, capturing the configure terminal log
                output_filename = script.create_output_filename("CONFIG-RESULTS")
                script.send_config_commands(config_commands, output_filename)
                # Set Rollback filename, in case this option is used
                rollback_filename = script.create_output_filename("ROLLBACK")

            # Save configuration
            script.save()

        # Check our settings to see if we should create a rollback.
        create_rollback = script.settings.getboolean("update_interface_desc", "rollback_file")
        if create_rollback:
            with open(rollback_filename, 'wb') as output_file:
                for command in rollback:
                    output_file.write("{}\n".format(command))

    # Return terminal parameters back to the original state.
    script.end_cisco_session()


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
        local_intf = utilities.long_int_name(entry[0])
        device_id = entry[1]
        system_name = entry[2]
        remote_intf = utilities.long_int_name(entry[3])
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


def get_desc_table(script):
    """
    A function that creates a lookup dictionary that can be used to get the description of an interface.

    :param script: The script object that represents this script being executed
    :type script: script_types.Script

    :return: A dictionary that allows getting the description of an interface by using the interface as the key.
    :rtype: dict
    """
    send_cmd = "show interface description"

    if script.os == "IOS":
        int_template = script.get_template("cisco_ios_show_interfaces_description.template")
    else:
        int_template = script.get_template("cisco_nxos_show_interface_description.template")

    raw_int_desc = script.get_command_output(send_cmd)
    desc_list = utilities.textfsm_parse_to_list(raw_int_desc, int_template)

    desc_table = {}
    # Change interface names to long versions for better matching with other outputs
    for entry in desc_list:
        intf = utilities.long_int_name(entry[0])
        desc_table[intf] = entry[1]

    return desc_table


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_script = script_types.CRTScript(crt)
    script_main(crt_script)

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_script = script_types.DirectScript(os.path.realpath(__file__))
    script_main(direct_script)
