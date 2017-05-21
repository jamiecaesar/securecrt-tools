# ###############################  MODULE  INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
#    !!!! NOTE:  THIS IS NOT A SCRIPT THAT CAN BE RUN IN SECURECRT. !!!!
#
# This is a Python module that contains simple utility functions that do not require the SecureCRT session information
# to function.
#
#

# #################################  IMPORTS   ##################################
import os
import re
import datetime
import csv

def get_date_string(format):
    """
    Returns the current date/time based on the format string supplied.

    :param format: A string used to describe the desired datetime format to be returned.  See
                    https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
    :return: Returns the current date/time based on the format string passed into the function.
    """
    now = datetime.datetime.now()
    this_date = now.strftime(format)
    return this_date


def expanded_path(base_path):
    """
    Returns the full path when a relative path is given.

    If the path starts with ~ (home directory), "\" (Windows) or doesn't begin with the posix root "/", then prepend 
    the user's home directory.

    :param base_path: 
    :return: 
    """
    if base_path[0:2] == "~/":
        base_path = os.path.join(os.path.expanduser('~'), base_path[2:])
    elif base_path[0] != "/" or base_path[0] != "\\":
        base_path = os.path.join(os.path.expanduser('~'), base_path)
    return base_path


def alphanum_key(s):
    """
    A key function to sort alpha-numerically
    
    From http://nedbatchelder.com/blog/200712/human_sorting.html
    This function can be used as the key for a sort algorithm to give it an understanding of numbers, 
    i.e. [a1, a2, a10], instead of the default (ASCII) sorting, i.e. [a1, a10, a2].
    
    :param s: 
    :return: 
    """
    return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', s)]


def read_file_to_string(file_path):
    """
    Reads a file into a string variable

    :param file_path:  Full path to the location of hte file to be read.
    :return:  A string containing the entire contents of the file.
    """
    with open(file_path, 'r') as input_file:
        file_data = input_file.read()

    return file_data


def read_file_to_list(file_path):
    """
    Reads a file and makes each line an entry into a list object.

    (e.g. [ "This is the first line", "This is the second line" ] ) and returns the list so it can be further processed.

    :param file_path:  Full path to the location of hte file to be read.
    :return:  A list of strings, each entry being a line in the file.
    """
    return [line.rstrip('\r\n') for line in open(file_path, 'r')]


def list_of_lists_to_csv(data, filename):
    """
    Takes a list of lists and writes it to a csv file.
    
    This function takes a list of lists, such as:

    [ ["IP", "Desc"], ["1.1.1.1", "Vlan 1"], ["2.2.2.2", "Vlan 2"] ]

    and writes it into a CSV file with the filename supplied.   Each sub-list
    in the outer list will be written as a row.  If you want a header row, it 
    must be the first sub-list in the outer list.
    
    :param data:  A list of lists data structure (one row per line of the CSV)
    :param filename:  The output filename for the CSV file
    """
    # Binary mode required ('wb') to prevent Windows from adding linefeeds after each line.
    newfile = open(filename, 'wb')
    csv_out = csv.writer(newfile)
    for line in data:
        csv_out.writerow(line)
    newfile.close()


def list_of_dicts_to_csv(fields, data, filename):
    """
    Accepts a list of dictionaries and writes it to a CSV file.
    
    This function takes a list of dicts (passed in as data), such as:

    [ {"key1": value, "key2": value}, {"key1": value, "key2": value} ]

    and puts it into a CSV file with the supplied filename.  The function requires 
    a list of the keys found in the dictionaries (passed in as fields), such as:

    [ "key1", "key2" ]

    This will write a CSV file with all of the keys as the header row, and add a
    row for every dict in the list, with the correct data in each column.

    :param fields:  The list of header fields
    :param data:   The list of dictionaries, where each key in the dict corresponds to a header value
    :param filename:  The output filename to write
    """
    with open(filename, "wb") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writerow(dict(zip(writer.fieldnames, writer.fieldnames)))
        for entry in data:
            writer.writerow(entry)


def fixed_columns_to_list(filepath, field_lens, ext='.txt'):
    '''
    Reads in the text input of a file (.txt default extension).  This file is 
    meant to hold a text table with fixed column widths (like "show mac 
    address-table" or "show int status").  

    The "field_lens" variable must be a tuple (i.e. (5, 10, 23, 14) ) which 
    has the column widths for each column.  Since the last column will often
    be as long as whatever output should fit there, without being truncated,
    the last value can be set to -1.  In this case, the script will detect 
    the longest line and select the last column width appropriately.

    For example:  (5, 10, 23, 14, -1) is a 5 column table, and the script
    will automatically detect the width of the last column.
    '''

    table = []
    list_of_lines = ReadFileToList(filepath, ext=ext)
    max_line = max([len(line) for line in list_of_lines])
    min_line_len = sum(list(field_lens)[:-1])
    fmtstring = ' '.join('{0}{1}'.format(fw if fw > 0 else str(max_line - min_line_len), 's') for fw in field_lens)
    fieldstruct = struct.Struct(fmtstring)
    parse = fieldstruct.unpack_from
    for line in list_of_lines:
        if len(line) >= min_line_len and len(line) < max_line:
            line = line + ' ' * (max_line - len(line))
            fields = parse(line)
            next_line = [item.strip(' -\r\n\t') for item in fields]
            if next_line[0]:
                table.append(next_line)
    return table