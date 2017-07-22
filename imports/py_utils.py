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