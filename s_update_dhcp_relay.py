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

def update_helpers(session, check_mode, old_helpers, new_helpers, remove_old_helpers):
    script = session.script
    # A list of supported OSes that this script is configured to handle.
    supported_os = ["IOS", "NXOS"]

    # Create data structure to record helper IPs that we find that aren't in our list that we are either looking for
    # or adding.
    unrecognized_helpers = [["Hostname", "Interface", "Helper IP"]]

    if session.os not in supported_os:
        logger.debug("<UPDATE_HELPER> OS is {0}, which is not in supported OS list of {1}"
                     .format(session.os, supported_os))
        raise sessions.UnsupportedOSError("This device's OS is {0}, which is not a supported OS for this script which "
                                          "only supports: {1}).".format(session.os, supported_os))

    # Save our "Before" configuration.
    before_filename = session.create_output_filename("1-show-run-BEFORE")
    session.write_output_to_file("show run", before_filename)

    # Open the "Before" configuration and parse it with TextFSM to find helper-addresses
    with open(before_filename, 'r') as config_file:
        run_config = config_file.read()

    if session.os == "IOS":
        template_file = script.get_template("cisco_ios_show_run_helper.template")
    else:
        template_file = script.get_template("cisco_nxos_show_run_dhcp_relay.template")

    result = utilities.textfsm_parse_to_list(run_config, template_file)

    if check_mode:
        os.remove(before_filename)

    # Create a dictionary that will let us get a set of configured helpers under each interface.
    intfs_with_helpers = {}
    for entry in result:
        interface = entry[0]
        helper = entry[1]
        vrf = entry[2]
        if interface in intfs_with_helpers:
            intfs_with_helpers[interface]["helpers"].add(helper)
        else:
            intfs_with_helpers[interface] = {"vrf": "{}".format(vrf), "helpers": {helper}}

        # Check if helper is unrecognized and needs to be recorded
        if helper not in old_helpers and helper not in new_helpers:
            unknown_line = [session.hostname, interface, helper, vrf]
            unrecognized_helpers.append(unknown_line)
            logger.debug("<UPDATE_HELPER> Adding {} to unknown helpers".format(str(unknown_line)))

    logger.debug("<UPDATE_HELPER> Interfaces with helpers:\n{}".format(str(intfs_with_helpers)))

    # Figure out which interfaces need additional helpers
    need_to_update = []
    for interface in intfs_with_helpers:
        configured_helpers = intfs_with_helpers[interface]["helpers"]
        vrf = intfs_with_helpers[interface]["vrf"]
        helper_matches = configured_helpers.intersection(old_helpers)
        if helper_matches:
            needed_new_helpers = set(new_helpers).difference(configured_helpers)
            if remove_old_helpers:
                need_to_update.append((interface, vrf, needed_new_helpers, helper_matches))
            else:
                need_to_update.append((interface, vrf, needed_new_helpers, {}))

    logger.debug("<UPDATE_HELPER> Required Updates:\n{}".format(str(need_to_update)))

    # If we have anything we need to update, build out required config commands, depending on device OS.
    update_commands = []
    if session.os == "IOS":
        for entry in need_to_update:
            interface = entry[0]
            vrf = entry[1]
            helpers_to_add = entry[2]
            helpers_to_remove = entry[3]
            if helpers_to_add or helpers_to_remove:
                update_commands.append("interface {}".format(interface))
                for helper in helpers_to_add:
                    if vrf == "":
                        update_commands.append("ip helper-address {}".format(helper))
                    elif vrf == "global":
                        update_commands.append("ip helper-address global {}".format(helper))
                    else:
                        update_commands.append("ip helper-address vrf {} {}".format(vrf, helper))
                for helper in helpers_to_remove:
                    if vrf == "":
                        update_commands.append("no ip helper-address {}".format(helper))
                    elif vrf == "global":
                        update_commands.append("no ip helper-address global {}".format(helper))
                    else:
                        update_commands.append("no ip helper-address vrf {} {}".format(vrf, helper))
    else:
        for entry in need_to_update:
            interface = entry[0]
            vrf = entry[1]
            helpers_to_add = entry[2]
            helpers_to_remove = entry[3]
            if helpers_to_add or helpers_to_remove:
                update_commands.append("interface {}".format(interface))
                for helper in helpers_to_add:
                    if vrf == "":
                        update_commands.append("ip dhcp relay address {}".format(helper))
                    else:
                        update_commands.append("ip dhcp relay address {} use-vrf {}".format(helper, vrf))
                for helper in helpers_to_remove:
                    if vrf == "":
                        update_commands.append("no ip dhcp relay address {}".format(helper))
                    else:
                        update_commands.append("no ip dhcp relay address {} use-vrf {}".format(helper, vrf))

    # Send config commands to the device and save the session.
    if update_commands:
        if check_mode:
            # If in Check Mode, only generate config updates and write to a file.
            logger.debug("<UPDATE_HELPER> CHECK MODE: Generating config")
            command_string = ""
            command_string += "configure terminal\n"
            for command in update_commands:
                command_string += "{}\n".format(command.strip())
            command_string += "end\n"

            config_filename = session.create_output_filename("PROPOSED_CONFIG")
            with open(config_filename, 'w') as output_file:
                output_file.write(command_string)
        else:
            config_filename = session.create_output_filename("2-CONFIG_RESULTS")
            session.send_config_commands(update_commands, output_filename=config_filename)
            session.save()

            # Save our "After" configuration.
            after_filename = session.create_output_filename("3-show-run-AFTER")
            session.write_output_to_file("show run", after_filename)


def build_valid_ip_list(text_ip_list):
    ip_list = []
    for text_ip in text_ip_list:
        try:
            ip_list.append(str(ipaddress.ip_address(unicode(text_ip))))
        except ipaddress.AddressValueError:
            raise ipaddress.AddressValueError("{0} is not a valid IPv4 or IPv6 address.  Please check your "
                                              "settings.ini file.".format(text_ip))
    return ip_list


def script_main(session):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will scan the running configuration of the connected device looking for instances of old IP helper/DHCP
    relay addresses (IOS/NXOS) on interfaces and if found will update the helper/relay addresses with the newer ones.
    The new and old addresses that the script looks for is saved in the settings.ini file, as documented below.

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
    * | **old_relays** - This is a comma separated list of IP addresses that the script should
      | search for as relay addresses in the device's configuration.
    * | **new_relays** - This is a comma separated list of IP addresses that are the new relay
      | addresses that should be added to any interface that has at least one of the old
      | helper/relay addresses on it.
    * | **remove_old_relays** - If True, the script will add the new relays and REMOVE the old
      | relays immediately after adding the new ones.  If False (default), the script will
      | only add the new relays to interfaces where at least one old relay is found.  This
      | is useful when you want to push out new relays as part of a migration process
      | without removing the old relays.  Since this script will not try to push new relay
      | addresses that already exist on an interface, the script can be run again with this
      | option set to True to later remove the old relays.

    :param session: A subclass of the sessions.Session object that represents this particular script session (either
                SecureCRTSession or DirectSession)
    :type session: sessions.Session

    """
    # Get script object that owns this session, so we can check settings, get textfsm templates, etc
    script = session.script

    # ----------------------------------- GET VALUES FROM SETTINGS -----------------------------------

    # Display instructions message, unless settings prevent it
    show_instructions = script.settings.getboolean("update_dhcp_relay", "show_instructions")
    if show_instructions:
        response = script.message_box("The list of old and new ip-helper/dhcp relay IPs can be edited in the "
                                      "'settings/settings.ini' file in the main securecrt-tools directory.\nSee the "
                                      "documentation for this script ('docs/index.html') for more details.\n\n"
                                      "Do you want to stop seeing this message?",
                                      "Instructions", ICON_QUESTION + BUTTON_YESNO)
        if response == IDYES:
            script.settings.update("update_dhcp_relay", "show_instructions", False)

    # Collection of old helpers/relays is in a set data structure to make membership checks easier.  A list works fine
    # for new helpers/relays.
    old_helpers = set(build_valid_ip_list(script.settings.getlist("update_dhcp_relay", "old_relays")))
    new_helpers = build_valid_ip_list(script.settings.getlist("update_dhcp_relay", "new_relays"))
    remove_old_helpers = script.settings.getboolean("update_dhcp_relay", "remove_old_relays")

    # ----------------------------------- PROMPT FOR CHECK-MODE -----------------------------------

    # Ask if this should be a test run (generate configs only) or full run (push updates to devices)
    check_mode_message = "Do you want to run this script in check mode? (Only generate configs)\n" \
                         "\n" \
                         "Yes = Connect to devices and generate change scripts\n" \
                         "No = Connect to devices and push configurations"
    logger.debug("<UPDATE_HELPER> Prompting the user to run in check mode.")
    result = script.message_box(check_mode_message, "Run in Check Mode?", ICON_QUESTION + BUTTON_YESNOCANCEL)
    if result == IDYES:
        check_mode = True
    elif result == IDNO:
        check_mode = False
    else:
        return

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    session.start_cisco_session()

    update_helpers(session, check_mode, old_helpers, new_helpers, remove_old_helpers)

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
    script_main(crt_session)
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
