# $language = "python"
# $interface = "1.0"

# ################################################   SCRIPT INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# This script will grab the route table information from a Cisco IOS or NXOS device and export details about each
# next-hop address (how many routes and from which protocol) into a CSV file.  It will also list all connected networks
# and give a detailed breakdown of every route that goes to each next-hop.
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
import securecrt_tools.ipaddress as ipaddress


# ################################################  LOAD SETTINGS   ###################################################

session_set_filename = os.path.join(script_dir, "settings", settings.global_settings_filename)
session_settings = settings.SettingsImporter(session_set_filename, settings.global_defs)


# ################################################     SCRIPT       ###################################################

def update_empty_interfaces(route_table):
    """
    Takes the routes table as a list of dictionaries (with dict key names used in parse_routes function) and does
    recursive lookups to find the outgoing interface for those entries in the route-table where the outgoing interface
    isn't listed.

    :param route_table: <list> A list of dictionaries - specifically with the keys 'network', 'protocol', 'nexthop'
                                and 'interface
    :return: The updated route_table object with outbound interfaces filled in.
    """

    def recursive_lookup(nexthop):
        for network in connected:
            if nexthop in network:
                return connected[network]
        for network in statics:
            if nexthop in network:
                return recursive_lookup(statics[network])
        return None

    logger.debug("STARTING update_empty_interfaces")
    connected = {}
    unknowns = {}
    statics = {}
    for route in route_table:
        if route['protocol'] == 'connected':
            connected[route['network']] = route['interface']
        if route['protocol'] == 'static':
            if route['nexthop']:
                statics[route['network']] = route['nexthop']
        if route['nexthop'] and not route['interface']:
            unknowns[route['nexthop']] = None

    for nexthop in unknowns:
        unknowns[nexthop] = recursive_lookup(nexthop)

    for route in route_table:
        if not route['interface']:
            if route['nexthop'] in unknowns:
                route['interface'] = unknowns[route['nexthop']]

    logger.debug("ENDING update_empty_interfaces")


def parse_routes(fsm_routes):
    """
    This function will take the TextFSM parsed route-table from the `textfsm_parse_to_dict` function.  Each dictionary
    in the TextFSM output represents a route entry.  Each of these dictionaries will be updated to convert IP addresses
    into ip_address or ip_network objects (from the ipaddress.py module).  Some key names will also be updated also.

    :param fsm_routes: <list of dicts> TextFSM output from the `textfsm_parse_to_dict` function.
    :return: <list of dicts> An updated list of dictionaries that replaces IP address strings with objects from the
                                ipaddress.py module from Google.
    """
    logger.debug("STARTING parse_routes function.")
    complete_table = []
    for route in fsm_routes:
        new_entry = {}

        logger.debug("Processing route entry: {0}".format(str(route)))
        new_entry['network'] = ipaddress.ip_network(u"{0}/{1}".format(route['NETWORK'], route['MASK']))

        new_entry['protocol'] = utils.normalize_protocol(route['PROTOCOL'])

        if route['NEXTHOP_IP'] == '':
            new_entry['nexthop'] = None
        else:
            new_entry['nexthop'] = ipaddress.ip_address(unicode(route['NEXTHOP_IP']))

        if route["NEXTHOP_IF"] == '':
            new_entry['interface'] = None
        else:
            new_entry['interface'] = route['NEXTHOP_IF']

        # Nexthop VRF will only occur in NX-OS route tables (%vrf-name after the nexthop)
        if 'NEXTHOP_VRF' in route:
            if route['NEXTHOP_VRF'] == '':
                new_entry['vrf'] = None
            else:
                new_entry['vrf'] = route['NEXTHOP_VRF']

        logger.debug("Adding updated route entry '{0}' based on the information: {1}".format(str(new_entry),
                                                                                             str(route)))
        complete_table.append(new_entry)

    update_empty_interfaces(complete_table)
    logger.debug("ENDING parse_route function")
    return complete_table


def nexthop_summary(textfsm_dict):
    """
    A function that builds a CSV output (list of lists) that displays the summary information after analyzing the
    input route table.

    :param textfsm_dict:
    :return:
    """
    # Identify connected or other local networks -- most found in NXOS to exlude from next-hops.  These are excluded
    # from the nexthop summary (except connected has its own section in the output).
    logger.debug("STARTING nexthop_summary function")
    local_protos = ['connected', 'local', 'hsrp', 'vrrp', 'glbp']

    # Create a list of all dynamic protocols from the provided route table.  Add total and statics to the front.
    proto_list = []
    for entry in textfsm_dict:
        if entry['protocol'] not in proto_list and entry['protocol'] not in local_protos:
            logger.debug("Found protocol '{0}' in the table".format(entry['protocol']))
            proto_list.append(entry['protocol'])
    proto_list.sort(key=utils.human_sort_key)
    proto_list.insert(0, 'total')
    proto_list.insert(0, 'interface')

    # Create dictionaries to store summary information as we process the route table.
    summary_table = {}
    connected_table = {}
    detailed_table = {}

    # Process the route table to populate the above 3 dictionaries.
    for entry in textfsm_dict:
        logger.debug("Processing route: {0}".format(str(entry)))
        # If the route is connected, local or an FHRP entry
        if entry['protocol'] in local_protos:
            if entry['protocol'] == 'connected':
                if entry['interface'] not in connected_table:
                    connected_table[entry['interface']] = []
                connected_table[entry['interface']].append(str(entry['network']))
        else:
            if entry['nexthop']:
                if 'vrf' in entry and entry['vrf']:
                    nexthop = "{0}%{1}".format(entry['nexthop'], entry['vrf'])
                else:
                    nexthop = str(entry['nexthop'])
            elif entry['interface'].lower() == "null0":
                nexthop = 'discard'

            if nexthop not in summary_table:
                # Create an entry for this next-hop, containing zero count for all protocols.
                summary_table[nexthop] = {}
                summary_table[nexthop].update(zip(proto_list, [0] * len(proto_list)))
                summary_table[nexthop]['interface'] = entry['interface']
            # Increment total and protocol specific count
            summary_table[nexthop][entry['protocol']] += 1
            summary_table[nexthop]['total'] += 1

            if nexthop not in detailed_table:
                detailed_table[nexthop] = []
            detailed_table[nexthop].append((str(entry['network']), entry['protocol']))

    # Convert summary_table into a format that can be printed to the CSV file.
    output = []
    header = ["Nexthop", "Interface", "Total"]
    header.extend(proto_list[2:])
    output.append(header)
    summary_keys = sorted(summary_table.keys(), key=utils.human_sort_key)
    for key in summary_keys:
        line = [key]
        for column in proto_list:
            line.append(summary_table[key][column])
        output.append(line)
    output.append([])

    # Convert the connected_table into a format that can be printed to the CSV file (and append to output)
    output.append([])
    output.append(["Connected:"])
    output.append(["Interface", "Network(s)"])
    connected_keys = sorted(connected_table.keys(), key=utils.human_sort_key)
    for key in connected_keys:
        line = [key]
        for network in connected_table[key]:
            line.append(network)
        output.append(line)
    output.append([])

    # Convert the detailed_table into a format that can be printed to the CSV file (and append to output)
    output.append([])
    output.append(["Route Details"])
    output.append(["Nexthop", "Network", "Protocol"])
    detailed_keys = sorted(detailed_table.keys(), key=utils.human_sort_key)
    for key in detailed_keys:
        for network in detailed_table[key]:
            line = [key]
            line.extend(list(network))
            output.append(line)
        output.append([])

    # Return the output, ready to be sent to directly to a CSV file
    logger.debug("ENDING nexthop_summary function")
    return output


def script_main(session):
    supported_os = ["IOS", "NXOS"]
    if session.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Exiting program.".format(session.os))
        session.message_box("{0} is not a supported OS for this script.".format(session.os), "Unsupported OS",
                            options=sessions.ICON_STOP)
        return
    else:
        send_cmd = "show ip route"

    selected_vrf = session.prompt_window("Enter the VRF name. (Leave blank for default VRF)")
    if selected_vrf != "":
        send_cmd = send_cmd + " vrf {0}".format(selected_vrf)
        session.hostname = session.hostname + "-VRF-{0}".format(selected_vrf)
        logger.debug("Received VRF: {0}".format(selected_vrf))

    raw_routes = session.get_command_output(send_cmd)

    if session.os == "IOS":
        template_file = "textfsm-templates/cisco_ios_show_ip_route.template"
    else:
        template_file = "textfsm-templates/cisco_nxos_show_ip_route.template"

    fsm_results = utils.textfsm_parse_to_dict(raw_routes, template_file)

    route_list = parse_routes(fsm_results)

    output_filename = session.create_output_filename("nexthop-summary", ext=".csv")
    output = nexthop_summary(route_list)
    utils.list_of_lists_to_csv(output, output_filename)

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