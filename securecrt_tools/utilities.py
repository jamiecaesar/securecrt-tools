# ################################################   MODULE INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# The module contains functions to process the outputs from network devices, or other python functions that help with
# processing data in our scripts.
#
#

# ################################################     IMPORTS      ###################################################
import csv
import re
import logging
import os

import securecrt_tools.textfsm as textfsm

# Get logger instance, if enabled when main script was launched.
logger = logging.getLogger("securecrt")


# ################################################    FUNCTIONS     ###################################################

def textfsm_parse_to_list(input_data, template_name, add_header=False):
    """
    Use TextFSM to parse the input text (from a command output) against the specified TextFSM template.   Use the
    default TextFSM output which is a list, with each entry of the list being a list with the values parsed.  Use
    add_header=True if the header row with value names should be prepended to the start of the list.

    :param input_data:  Path to the input file that TextFSM will parse.
    :param template_name:  Path to the template file that will be used to parse the above data.
    :param add_header:  When True, will return a header row in the list.  This is useful for directly outputting to CSV.
    :return: The TextFSM output (A list with each entry being a list of values parsed from the input)
    """

    logger.debug("Preparing to process with TextFSM and return a list of lists")
    # Create file object to the TextFSM template and create TextFSM object.
    logger.debug("Using template at: {0}".format(template_name))
    with open(template_name, 'r') as template:
        fsm_table = textfsm.TextFSM(template)

    # Process our raw data vs the template with TextFSM
    output = fsm_table.ParseText(input_data)
    logger.debug("TextFSM returned a list of size: '{0}'".format(len(output)))

    # Insert a header row into the list, so that when output to a CSV there is a header row.
    if add_header:
        logger.debug("'Adding header '{0}' to start of output list.".format(fsm_table.header))
        output.insert(0, fsm_table.header)

    return output


def textfsm_parse_to_dict(input_data, template_filename):
    """
    Use TextFSM to parse the input text (from a command output) against the specified TextFSM template.   Convert each
    list from the output to a dictionary, where each key in the TextFSM Value name from the template file.

    :param input_data:  Path to the input file that TextFSM will parse.
    :param template_filename:  Path to the template file that will be used to parse the above data.
    :return: A list, with each entry being a dictionary that maps TextFSM variable name to corresponding value.
    """

    logger.debug("Preparing to process with TextFSM and return a list of dictionaries.")
    # Create file object to the TextFSM template and create TextFSM object.
    logger.debug("Using template at: {0}".format(template_filename))
    with open(template_filename, 'r') as template:
        fsm_table = textfsm.TextFSM(template)

    # Process our raw data vs the template with TextFSM
    fsm_list = fsm_table.ParseText(input_data)
    logger.debug("TextFSM returned a list of size: '{0}'".format(len(fsm_list)))

    # Insert a header row into the list, so that when output to a CSV there is a header row.
    header_list = fsm_table.header

    # Combine the header row with each entry in fsm_list to create a dictionary representation.  Add to output list.
    output = []
    for entry in fsm_list:
        dict_entry = dict(zip(header_list, entry))
        output.append(dict_entry)

    logger.debug("Converted all sub-lists to dicts.  Size is {0}".format(len(output)))
    return output


def list_of_lists_to_csv(data, filename):
    """
    Takes a list of lists and writes it to a csv file.

    This function takes a list of lists, such as:

    [ ["IP", "Desc"], ["1.1.1.1", "Vlan 1"], ["2.2.2.2", "Vlan 2"] ]

    and writes it into a CSV file with the filename supplied.   Each sub-list in the outer list will be written as a
    row.  If you want a header row, it must be the first sub-list in the outer list.

    :param data: <2d-list>  A list of lists data structure (one row per line of the CSV)
    :param filename: <str>  The output filename for the CSV file, that will be placed in the 'save path' directory under
                            the global settings.
    """
    # Validate path before creating file.
    logger.debug("Opening file {0} for writing".format(filename))
    with open(filename, 'wb') as output_csv:
        # Binary mode required ('wb') to prevent Windows from adding linefeeds after each line.
        csv_out = csv.writer(output_csv)
        for line in data:
            logger.debug("Writing row: '{0}'".format(line))
            csv_out.writerow(line)
    logger.debug("Completed writing to file {0}".format(filename))


def list_of_dicts_to_csv(data, filename, header, add_header=True):
    """

    :param data:
    :param filename:
    :param header:
    :return:
    """
    # Validate path before creating file.
    logger.debug("Opening file {0} for writing".format(filename))
    with open(filename, 'wb') as output_csv:
        csv_writer = csv.DictWriter(output_csv, fieldnames=header)
        if add_header:
            csv_writer.writeheader()
        for entry in data:
            csv_writer.writerow(entry)
    logger.debug("Completed writing to file {0}".format(filename))


def extract_system_name(device_id, strip_list=[]):
    """
    In the CDP output some systems return a Hostname(Serial Number) format, while others return Serial(Hostname) output.
    This function tries to extract the system name from the CDP output and ignore the serial number.

    :param device_id: The device_id as learned from CDP.
    :param strip_list: A list of strings that should be removed from the hostname, if found
    :return:
    """
    cisco_serial_format = r'[A-Z]{3}[A-Z0-9]{8}'
    ip_format = r'\d{1-3}\.\d{1-3}\.\d{1-3}\.\d{1-3}'
    re_serial = re.compile(cisco_serial_format)
    re_ip = re.compile(ip_format)

    # Add a leading "." in front of all domains in the strip_list before processing
    strip_list = [".{0}".format(entry) for entry in strip_list if entry[0] != "."]

    # If we find an open paren, then we either have "SYSTEM_NAME(SERIAL)" or "SERIAL(SYSTEM-NAME)" format.  The latter
    # format is often seen in older devices.  Determine which is the system_name by matching regex for a Cisco serial.
    logger.debug("Analyzing '{0}".format(device_id))
    if "(" in device_id:
        logger.debug("Found '(' in device_id.")
        left, right = device_id.split('(')
        right = right.strip(')')
        left_serial = re_serial.match(left)
        right_serial = re_serial.match(right)
        if right_serial:
            system_name = left
            logger.debug("Detected right side ({0}) is a serial number.".format(right))
        elif left_serial:
            system_name = right
            logger.debug("Detected left side ({0}) is a serial number.".format(left))
        else:
            system_name = device_id
            logger.debug("Didn't find anything to remove.")
    else:
        system_name = device_id
        logger.debug("Didn't find anything to remove.")

    # If FQDN, only take the host portion, otherwise return what we have.
    if "." in system_name:
        is_ip = re_ip.match(system_name)
        # Some device return IP as device_id.  In those cases, just return IP -- don't treat it like FQDN
        if is_ip:
            logger.debug("Device ID is an IP address ({0})".format(device_id))
            return system_name
        else:
            for item in strip_list:
                if item in system_name:
                    logger.debug("Stripping '{0}' from {1}".format(item, system_name))
                    system_name = system_name.replace(item, '')
            return system_name
    else:
        return system_name


def short_int_name(long_name):
    """
    This function shortens the interface name for easier reading

    :param long_name:  The input string (long interface name)
    :return:  The shortened interface name
    """
    replace_pairs = [
        ('fortygigabitethernet', 'Fo'),
        ('tengigabitethernet', 'Te'),
        ('gigabitethernet', 'Gi'),
        ('fastethernet', 'Fa'),
        ('ethernet', 'Eth'),
        ('port-channel', 'Po'),
        ('loopback', "Lo")
    ]
    lower_str = long_name.lower()
    for pair in replace_pairs:
        if pair[0] in lower_str:
            return lower_str.replace(pair[0], pair[1])
    else:
        return long_name


def long_int_name(short_name):
    """
    This function expands a short interface name to the full name

    :param short_name:  The input string (short interface name)
    :return:  The shortened interface name
    """
    replace_pairs = [
        (r'Fo', 'FortyGigabitEthernet'),
        (r'Te', 'TenGigabitEthernet'),
        (r'Gi', 'GigabitEthernet'),
        (r'Fa', 'FastEthernet'),
        (r'Eth', 'Ethernet'),
        (r'e', 'Ethernet'),
        (r'Po', 'port-channel'),
        (r'Lo', 'Loopback')
    ]
    for pair in replace_pairs:
        if re.match("{0}\d".format(pair[0]), short_name, re.IGNORECASE):
            return short_name.replace(pair[0], pair[1])
    else:
        return short_name


def normalize_protocol(raw_protocol):
    """
    A function to normalize protocol names between IOS and NXOS.  For example, IOS uses 'C' and NXOS uses 'direct" for
    connected routes.  This function will return 'connected' in both cases.

    :param raw_protocol: <str> The protocol value found in the route table output
    :return: A normalized name for that type of route.
    """
    if raw_protocol[0] == 'S' or "static" in raw_protocol:
        return 'static'
    elif raw_protocol[0] == 'C' or 'direct' in raw_protocol:
        return 'connected'
    elif raw_protocol[0] == 'L' or 'local' in raw_protocol:
        return 'local'
    elif raw_protocol[0] == 'D':
        return 'eigrp'
    elif raw_protocol[0] == 'O':
        return 'ospf'
    elif raw_protocol[0] == 'B':
        return 'bgp'
    elif raw_protocol[0] == 'i':
        return 'isis'
    elif raw_protocol[0] == 'R':
        return 'rip'
    else:
        return raw_protocol


def expand_number_range(num_string):
    """
    A function that will accept a text number range (such as 1,3,5-7) and convert it into a list of integers such as
    [1, 3, 5, 6, 7]

    :param num_string: <str> A string that is in the format of a number range (e.g. 1,3,5-7)
    :return: <list> A list of all integers in that range (e.g. [1,3,5,6,7])
    """
    output_list = []
    for item in num_string.split(','):
        if "-" in item:
            if item.count('-') != 1:
                raise ValueError("Invalid range: '{0]'".format(item))
            else:
                start, end = map(int, item.split('-'))
                output_list.extend(range(start, end+1))
        else:
            output_list.append(int(item))
    return output_list


def human_sort_key(s):
    """
    A key function to sort alpha-numerically, not by string

    From http://nedbatchelder.com/blog/200712/human_sorting.html
    This function can be used as the key for a sort algorithm to give it an understanding of numbers,
    i.e. [a1, a2, a10], instead of the default (ASCII) sorting, i.e. [a1, a10, a2].

    :param s:
    :return:
    """
    return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', s)]


def remove_empty_or_invalid_file(l_filename):
    """
    Check if file is empty or if we captured an error in the command.  If so, delete the file.

    :param l_filename: Name of file to check
    """
    # If file isn't empty (greater than 3 bytes)
    # Some of these file only save one CRLF, and so we can't match on 0
    # bytes
    file_size = os.path.getsize(l_filename)
    if 100 > file_size > 3:
        # Open the file we just created.
        with open(l_filename, "r") as new_file:
            lines = new_file.readlines()[0:3]
        # If the file only contains invalid command error, delete it.
        for line in lines:
            if re.match(r"^\W+\^|^%\W+invalid|^%\W+incomplete|^invalid", line, flags=re.I):
                new_file.close()
                os.remove(l_filename)
                break
        else:
            new_file.close()
    # If the file is empty, delete it
    elif file_size <= 3:
        os.remove(l_filename)