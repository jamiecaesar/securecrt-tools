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
from securecrt_tools import ipaddress

# Create global logger so we can write debug messages from any function (if debug mode setting is enabled in settings).
logger = logging.getLogger("securecrt")
logger.debug("Starting execution of {}".format(script_name))


# ################################################   SCRIPT LOGIC   ###################################################

def script_main(script, ask_vrf=True, vrf=None):
    """
    | SINGLE device script
    | Author: Jamie Caesar
    | Email: jcaesar@presidio.com

    This script will grab the route table information from a Cisco IOS or NXOS device and export details about each
    next-hop address (how many routes and from which protocol) into a CSV file.  It will also list all connected
    networks and give a detailed breakdown of every route that goes to each next-hop.

    :param script: A subclass of the sessions.Session object that represents this particular script session (either
                    SecureCRTSession or DirectSession)
    :type script: script_types.Script
    :param ask_vrf: A boolean that specifies if we should prompt for which VRF.  The default is true, but when this
        module is called from other scripts, we may want avoid prompting and supply the VRF with the "vrf" input.
    :type ask_vrf: bool
    :param vrf: The VRF that we should get the route table from.  This is used only when ask_vrf is False.
    :type vrf: str
    """
    # Create logger instance so we can write debug messages (if debug mode setting is enabled in settings).
    logger = logging.getLogger("securecrt")
    logger.debug("Starting execution of {}".format(script_name))

    # Start session with device, i.e. modify term parameters for better interaction (assuming already connected)
    script.start_cisco_session()

    # Validate device is running a supported OS
    supported_os = ["IOS", "NXOS"]
    if script.os not in supported_os:
        logger.debug("Unsupported OS: {0}.  Raising exception.".format(script.os))
        raise script_types.UnsupportedOSError("Remote device running unsupported OS: {0}.".format(script.os))

    send_cmd = "show ip route"

    # If we should prompt for a VRF, then do so.  Otherwise use the VRF passed into the function (if any)
    if ask_vrf:
        selected_vrf = script.prompt_window("Enter the VRF name. (Leave blank for default VRF)")
    else:
        selected_vrf = vrf

    # If we have a VRF, modify our commands and hostname to reflect it.  If not, pull the default route table.
    if selected_vrf:
        send_cmd = send_cmd + " vrf {0}".format(selected_vrf)
        script.hostname = script.hostname + "-VRF-{0}".format(selected_vrf)
        logger.debug("Received VRF: {0}".format(selected_vrf))

    raw_routes = script.get_command_output(send_cmd)

    if script.os == "IOS":
        template_file = script.get_template("cisco_ios_show_ip_route.template")
    else:
        template_file = script.get_template("cisco_nxos_show_ip_route.template")

    fsm_results = utilities.textfsm_parse_to_dict(raw_routes, template_file)

    route_list = parse_routes(fsm_results)

    output_filename = script.create_output_filename("nexthop-summary", ext=".csv")
    output = nexthop_summary(route_list)
    utilities.list_of_lists_to_csv(output, output_filename)

    # Return terminal parameters back to the original state.
    script.end_cisco_session()


def update_empty_interfaces(route_table):
    """
    Takes the routes table as a list of dictionaries (with dict key names used in parse_routes function) and does
    recursive lookups to find the outgoing interface for those entries in the route-table where the outgoing interface
    isn't listed.

    :param route_table: Route table information as a list of dictionaries (output from TextFSM)
    :type route_table: list of dict

    :return: The updated route_table object with outbound interfaces filled in.
    :rtype: list of dict
    """

    def recursive_lookup(nexthop):
        """
        Recursively looks up a route to find the actual next-hop on a connected network.

        :param nexthop: The next-hop IP that we are looking for
        :type nexthop: securecrt_tools.ipaddress

        :return: The directly connected next-hop for the input network.
        :rtype: securecrt_tools.ipaddress
        """
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

    :param fsm_routes: TextFSM output from the `textfsm_parse_to_dict` function.
    :type fsm_routes: list of dict

    :return: An updated list of dictionaries that replaces IP address strings with objects from the ipaddress.py module
    :rtype: list of dict
    """
    logger.debug("STARTING parse_routes function.")
    complete_table = []
    for route in fsm_routes:
        new_entry = {}

        logger.debug("Processing route entry: {0}".format(str(route)))
        new_entry['network'] = ipaddress.ip_network(u"{0}/{1}".format(route['NETWORK'], route['MASK']))

        new_entry['protocol'] = utilities.normalize_protocol(route['PROTOCOL'])

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

    :param textfsm_dict: The route table information in list of dictionaries format.
    :type textfsm_dict: list of dict

    :return: The nexthop summary information in a format that can be easily written to a CSV file.
    :rtype: list of lists
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
    proto_list.sort(key=utilities.human_sort_key)
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
    summary_keys = sorted(summary_table.keys(), key=utilities.human_sort_key)
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
    connected_keys = sorted(connected_table.keys(), key=utilities.human_sort_key)
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
    detailed_keys = sorted(detailed_table.keys(), key=utilities.human_sort_key)
    for key in detailed_keys:
        for network in detailed_table[key]:
            line = [key]
            line.extend(list(network))
            output.append(line)
        output.append([])

    # Return the output, ready to be sent to directly to a CSV file
    logger.debug("ENDING nexthop_summary function")
    return output


# ################################################  SCRIPT LAUNCH   ###################################################

# If this script is run from SecureCRT directly, use the SecureCRT specific class
if __name__ == "__builtin__":
    crt_script = script_types.CRTScript(crt)
    script_main(crt_script)

# If the script is being run directly, use the simulation class
elif __name__ == "__main__":
    direct_script = script_types.DirectScript(os.path.realpath(__file__))
    script_main(direct_script)
