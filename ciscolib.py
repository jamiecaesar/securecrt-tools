# $language = "python"
# $interface = "1.0"

################################  MODULE  INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
#
#    !!!! NOTE:  THIS IS NOT A SCRIPT THAT CAN BE RUN IN SECURECRT. !!!!
#
# This is a Python module that contains many common functions that would be used
# in other scripts.  Functions from this file can be imported into other scripts
# directly, preventing the need to maintain multiple copies of the same 
# functions in multiple scripts.
#
#

##################################  IMPORTS   ##################################
import os
import sys
import time
import datetime
import csv
import re
import struct


############################  MESSAGEBOX CONSTANTS  ############################
#
# These are used for MessageBox creation.  
#
# Button parameter options.  These can be OR'd ( | ) together to combine one
# from each category.
#
# Options to display icons
ICON_STOP = 16                 # display the ERROR/STOP icon.
ICON_QUESTION = 32             # display the '?' icon
ICON_WARN = 48                 # display a '!' icon.
ICON_INFO= 64                  # displays "info" icon.
#
# Options to choose what types of buttons are available
BUTTON_OK = 0                  # OK button only
BUTTON_CANCEL = 1              # OK and Cancel buttons
BUTTON_ABORTRETRYIGNORE = 2    # Abort, Retry, and Ignore buttons
BUTTON_YESNOCANCEL = 3         # Yes, No, and Cancel buttons
BUTTON_YESNO = 4               # Yes and No buttons
BUTTON_RETRYCANCEL = 5         # Retry and Cancel buttons
#
# Options for which button is default
DEFBUTTON1 = 0        # First button is default
DEFBUTTON2 = 256      # Second button is default
DEFBUTTON3 = 512      # Third button is default 
#
#
# Possible MessageBox() return values
IDOK = 1              # OK button clicked
IDCANCEL = 2          # Cancel button clicked
IDABORT = 3           # Abort button clicked
IDRETRY = 4           # Retry button clicked
IDIGNORE = 5          # Ignore button clicked
IDYES = 6             # Yes button clicked
IDNO = 7              # No button clicked


#################################  FUNCTIONS   #################################


def GetPrompt(tab):
    '''
    This function will capture the prompt of the device.  The script will 
    capture the text that is sent back from the remote device, which includes 
    what we typed being echoed back to us, so we have to account for that while 
    we parse data.
    '''
    #Send two line feeds
    tab.Send("\n\n")
    
    # Waits for first linefeed to be echoed back to us
    tab.WaitForString("\n") 
    
    # Read the text up to the next linefeed.
    prompt = tab.ReadString("\n") 

    #Remove any trailing control characters
    prompt = prompt.strip()

    # Get out of config mode if that is the active mode when the script was launched
    if "(co" in prompt:
        tab.Send("end\n")
        prompt = prompt.split("(")[0] + "#"
        tab.WaitForString(prompt)
        # Return the hostname (everything before the first "(")
        return prompt
        
    # Else, Return the hostname (all of the prompt except the last character)        
    else:
        return prompt


def GetTermInfo(session):
    '''
    A function that returns the current terminatl length and width
    '''

    re_num = r'\d+'
    reNum = re.compile(re_num)

    result = CaptureOutput(session, "show terminal | i Length")
    dim = result.split(',')
    
    return (reNum.search(dim[0]).group(0), reNum.search(dim[1]).group(0))


def valid_settings(imported):
    ''' 
    A function that validates the settings file is up-to-date
    '''
    all_settings = ['savepath', 'date_format', 'delete_temp', 'show_all_VLANs', 'modify_term']
    for setting in all_settings:
        if setting not in imported:
            return False
    return True


def StartSession(crt):
    '''
    A function that just encapsulates all the usual session start commands, 
    as well as gets the prompt so that other functions know when command output
    is complete.

    A dictionary of session information is returned for use by other functions.

    The crt object has to be passed in because the module has no way to import
    the SecureCRT specific modules.
    '''
    
    # Create data structure to store our session data.  Additional info added later.
    session = {}

    # Add the script directory to the python path (if not there) so we can import modules.
    script_dir = os.path.dirname(crt.ScriptFullName)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # Import Settings from Settings File or Default settings
    try:
        from script_settings import settings
    except ImportError:
        import shutil
        src_file = os.path.join(script_dir, 'script_settings_default.py')
        dst_file = os.path.join(script_dir, 'script_settings.py')
        try:
            shutil.copy(src_file, dst_file)
            setting_msg = ("Personal settings file created in directory:\n'{}'\n\n"
                           "Please edit this file to make any settings changes."
                           "**You MUST restart SecureCRT after edits to settings.**"
                           ).format(script_dir)
            crt.Dialog.MessageBox(setting_msg, "Settings Created", ICON_INFO)
            from script_settings import settings
        except IOError:
            err_msg =   ('Cannot find settings file.\n\nPlease make sure either the file\n'
                        '"script_settings_default.py"\n exists in the directory:\n"{}"\n'.format(script_dir)
                        )
            crt.Dialog.MessageBox(str(err_msg), "Settings Error", ICON_STOP)
            exit(0)

    if not valid_settings(settings):
        err_msg =   ('The current script_setings file is missing settings.\n'
                    'Overwrite "script_settings.py" with script_settings_default.py" and update your settings.\n\n'
                    '**Reload SecureCRT after making settings changes!**'
                    )
        crt.Dialog.MessageBox(str(err_msg), "Settings Error", ICON_STOP)
        exit(0)
    else:
        session['settings'] = settings


    # Create a "Tab" object, so that all the output goes into the correct Tab.
    objTab = crt.GetScriptTab()

    # Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"
    tab = objTab.Screen

    session['crt'] = crt
    session['tab'] = tab
    
    # Set Tab parameters to allow correct sending/receiving of data via SecureCRT
    tab.Synchronous = True
    tab.IgnoreEscape = True

    #Get the prompt of the device
    prompt = GetPrompt(tab)
    # Check for non-enable mode (prompt ends with ">" instead of "#")
    if prompt[-1] == ">": 
        crt.Dialog.MessageBox("Not in enable mode.  Enter enable and try again.", 
            "Not in Enable Mode", ICON_STOP)
        EndSession(session)
        sys.exit()
    elif prompt[-1] != "#":
        crt.Dialog.MessageBox("Unable to capture prompt.  Stopping script.",
            "Prompt Error", ICON_STOP)
        EndSession(session)
        sys.exit()
    else:
        session['prompt'] = prompt
        session['hostname'] = prompt[:-1]

        session['termlength'], session['termwidth'] = GetTermInfo(session)

        # Detect and store the OS of the attached device
        DetectNetworkOS(session)

        if settings['modify_term']:
            # Send term length command and wait for prompt to return
            tab.Send('term length 0\n')
            tab.WaitForString(prompt)

            # Send term width command and wait for prompt to return
            if session['OS'] == "NX-OS":
                tab.Send('term width 511\n')
            else:
                tab.Send('term width 0\n')
            tab.WaitForString(prompt)
        
        # Added due to Nexus echoing twice if system hangs and hasn't printed the prompt yet.
        # Seems like maybe the previous WaitFor prompt isn't working correctly always.  Something to look into.
        time.sleep(0.1)

    return session


def EndSession(session):
    '''
    A function to reverse the changes set by the StartSession function.

    sys.exit() can't be included here or else SecureCRT catches an exception
    and creates a pop-up after every script ends.
    '''
    # If the 'tab' and 'prompt' options aren't in the session structure, then
    # we aren't actually connected to any devices when this is called, and 
    # there is nothing to do.
    if session['tab'] and session['prompt']:
        tab = session['tab']
        prompt = session['prompt']
    
        len_str = 'term length {0}\n'.format(session['termlength'])
        width_str = 'term width {0}\n'.format(session['termwidth'])
    
        settings = session['settings']
        if settings['modify_term']:
            # Set term length back to saved values
            tab.Send(len_str)
            tab.WaitForString(prompt)
    
            # Set term width back to saved values
            tab.Send(width_str)
            tab.WaitForString(prompt)
    
        tab.Synchronous = False
        tab.IgnoreEscape = False


def DetectNetworkOS(session):
    '''
    A function to discover the OS of the connected session and adds an item
    to the session dictionary, so that other functions can reference it.
    '''
    SendCmd = "show version | i Cisco"

    version = CaptureOutput(session, SendCmd)
    ver_lines = version.split("\n")

    if "IOS XE" in ver_lines[0]:
        session['OS'] = "IOS XE"
    elif "Cisco IOS Software" in ver_lines[0] or \
         "Cisco Internetwork Operating System" in ver_lines[0]:
        session['OS'] = "IOS"
    elif "Cisco Nexus Operating System" in ver_lines[0]:
        session['OS'] = "NX-OS"
    else:
        session['OS'] = "Unknown"


def GetDateString(format):
    '''
    Simple function to format the current date/time based on the supplied format
    string.
    '''
    now = datetime.datetime.now()
    this_date = now.strftime(format)
    return this_date


def ExpandPath(base_path):
    # If the path starts with ~ (home directory), "\" (Windows) or doesn't begin
    # with the posix root "/", then prepend the user's home directory.
    if base_path[0:2] == "~/":
        base_path = os.path.join(os.path.expanduser('~'), base_path[2:])
    elif base_path[0] != "/" or base_path[0] != "\\":
        base_path = os.path.join(os.path.expanduser('~'), base_path)
    return base_path


def VerifyDirectory(session, base_dir, create=True):
    crt = session['crt']

    # Verify that base_path is valid absolute path, or else error and exit.    
    if not os.path.isabs(base_dir):
        error_str = 'Path is invalid. Please correct\n' \
                    'the path in the script settings.\n' \
                    'Path: {0}'.format(base_path)
        crt.Dialog.MessageBox(error_str, "Path Error", ICON_STOP)
        EndSession(session)
        sys.exit()

    # Check if directory exists.  If not, prompt to create it.    
    if not os.path.exists(os.path.normpath(base_dir)):
        if create:
            message_str = "The path: '{0}' does not exist.  Press OK to " \
                          "create, or cancel.".format(base_dir)
            result = crt.Dialog.MessageBox(message_str, "Create Directory?", ICON_QUESTION | 
                BUTTON_CANCEL | DEFBUTTON2)
    
            if result == IDOK:
                os.makedirs(base_dir)
            else:
                crt.Dialog.MessageBox("Save path does not exist.  Exiting.", 
                    "Invalid Path", ICON_STOP)
                EndSession(session)
                sys.exit()
        else:
            message_str = "The path: '{0}' does not exist.  Exiting.".format(base_dir)
            crt.Dialog.MessageBox(message_str, "Invalid Path", ICON_STOP)
            EndSession(session)
            sys.exit()


def GetAbsolutePath(session, base_path, filename, create=True):
    '''
    Function that builds the full path to the filename based on the information
    provided, as well as performing checks on the existence of the directory and
    prompting to create it if needed.
    '''
    crt = session['crt']

    exp_path = ExpandPath(base_path)
    VerifyDirectory(session, exp_path, create)
    return os.path.normpath(os.path.join(exp_path, filename))


def GetFilename(session, settings, desc):
    '''
    This function takes information from the settings and generates the 
    filename that can be passed to other functions to read/write files.  

    The filename is then passed to another function to verify it is 
    valid and check/prompt if the directory exists.
    '''
    # Extract path and format information from our tuple
    crt = session['crt']
    save_path = settings['savepath']
    date_format = settings['date_format']

    # If environment vars were used, expand them
    save_path = os.path.expandvars(save_path)

    # Extract hostname from the session information
    hostname = session['hostname']

    # Get the current date in the format supplied in date_format
    mydate = GetDateString(date_format)
    
    # Create Filename based on hostname and date format string.
    filebits = [hostname, desc, mydate]
    filename = '-'.join(filebits)
    file_path = GetAbsolutePath(session, save_path, filename)

    return file_path


def CaptureOutput(session, command):
    '''
    This function captures the raw output of the command supplied and returns
    it as a string.
    '''
    # Extract tab and prompt data
    prompt = session['prompt']
    tab = session['tab']

    #Send command
    tab.Send(command + '\n')

    #Ignore the echo of the command we typed
    tab.WaitForString(command.strip())
    
    #Capture the output until we get our prompt back and write it to the file
    result = tab.ReadString(prompt)

    return result.strip('\r\n')


def WriteOutput(session, command, filename, ext=".txt", writemode="wb"):
    '''
    This function captures the raw output of the command supplied and writes
    it to a file.

    This function was written specifically to write this way (line by line) 
    because dumping large outputs into a variable will cause SecureCRT to 
    bog down until it freezes.  This method can handle any length of output
    (like those big "show-tech"s)

    The default extension is .txt, unless another extension 
    is supplied. 
    '''
    prompt = session['prompt']
    tab = session['tab']

    matches=["\r\n", '--More--', prompt]
    try:
        newfile = open(filename + ext, writemode)
    except IOError, err:
        crt = session['crt']
        error_str = "IO Error for:\n{0}\n\n{1}".format(filename, err)
        crt.Dialog.MessageBox(err, "IO Error", ICON_STOP)

    # Send command
    tab.Send(command + "\n")

    # Ignore the echo of the command we typed (including linefeed)
    tab.WaitForString(command.strip())

    # Loop to capture every line of the command.  If we get CRLF (first entry
    # in our "endings" list), then write that line to the file.  If we get
    # our prompt back (which won't have CRLF), break the loop b/c we found the
    # end of the output.
    while True:
        nextline = tab.ReadString(matches)
        # session['crt'].Dialog.MessageBox('{}-{}'.format(str(tab.MatchIndex), nextline))
        # If the match was the 1st index in the endings list -> \r\n
        if tab.MatchIndex == 1:
            # Strip newlines from front and back of line.
            nextline = nextline.strip('\r\n')
            # If there is something left, write it.
            if nextline != "":
                # Strip line endings from line.  Also re-encode line as ASCII
                # and ignore the character if it can't be done (rare error on 
                # Nexus)
                newfile.write(nextline.strip('\r\n').encode('ascii', 'ignore') + 
                    "\r\n")
        elif tab.MatchIndex == 2:
            tab.Send(" ")
            if session['OS'] == 'IOS':
                tab.WaitForString("         ")
        elif tab.MatchIndex == 3:
            # We got our prompt, so break the loop
            break
    
    newfile.close()
    

def ReadFileToList(filepath, ext=".txt"):
    '''
    Reads in a file (default extension .txt), and puts each line as an entry of
    a list (i.e. [ "This is the first line", "This is the second line" ] ) and
    returns the list so it can be further processed.
    '''

    return [line.rstrip('\n') for line in open(filepath + ext)]


def FixedColumnsToList(filepath, field_lens, ext='.txt'):
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


def ListToCSV(data, filename, suffix=".csv", mode="wb"):
    '''
    This function takes a list of lists, such as:
    
    [ ["IP", "Desc"], ["1.1.1.1", "Vlan 1"], ["2.2.2.2", "Vlan 2"] ]

    and writes it into a CSV file with the filename supplied.   Each sub-list
    in the outer list will be written as a row.  If you want a header row, it 
    must be the first sub-list in the outer list.
    
    The default extension is .csv unless a different one is passed in.
    '''

    newfile = open(filename + suffix, mode)
    csvOut = csv.writer(newfile)
    for line in data:
        csvOut.writerow(line)
    newfile.close()


def DictListToCSV(fields, data, filename, ext=".csv", mode="wb"):
    '''
    This function takes a list of dicts (passed in as data), such as:
    
    [ {"key1": value, "key2": value}, {"key1": value, "key2": value} ]
    
    and puts it into a CSV file with the supplied filename.  The function requires 
    a list of the keys found in the dictionaries (passed in as fields), such as:
    
    [ "key1", "key2" ]
    
    This will write a CSV file with all of the keys as the header row, and add a
    row for every dict in the list, with the correct data in each column.

    The default extension is .csv unless a different one is passed in.
    '''

    with open(filename + ext, mode) as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writerow(dict(zip(writer.fieldnames, writer.fieldnames)))
        for entry in data:
            writer.writerow(entry)


def ParseIOSRoutes(routelist):
    '''
    This function parses the raw IOS route table into a datastucture that can 
    be used to more easily extract information.  The data structure that is 
    returned in a list of dictionaries.  Each dictionary entry represents an 
    entry in the route table and contains the following keys:
    
    {"protocol", "network", "AD", "metric", "nexthop", "lifetime", "interface"}
    
    '''

    routetable = []
    # Various RegEx expressions to match varying parts of a route table line
    # I did it this way to break up the regex into more manageable parts, 
    # Plus some of these parts can be found in mutliple line types
    # I'm also using named groups to more easily extract the needed data.
    #
    # Protocol (letter code identifying route entry)
    re_prot= r'(?P<protocol>\w[\* ][\w]{0,2})[ ]+'
    # Matches network address of route:  x.x.x.x/yy
    re_net = r'(?P<network>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d+)?)[ ]+'
    # Matches the Metric and AD: i.e. [110/203213]
    re_metric = r'\[(?P<ad>\d+)/(?P<metric>\d+)\][ ]+'
    # Matches the next hop in the route statement - "via y.y.y.y"
    re_nexthop = r'via (?P<nexthop>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}),?[ ]*'
    # Matches the lifetime of the route, usually in a format like 2m3d. Optional
    re_lifetime = r'(?P<lifetime>[\w:]+)?(, )?'
    # Matches outgoing interface. Not all protocols track this, so it is optional
    re_interface = r'(?P<interface>[\w-]+[\/\.\d]*)?'

    # Combining expressions above to build possible lines found in the route table
    #
    # Single line route entry
    re_single = re_prot + re_net + re_metric + re_nexthop + re_lifetime + re_interface
    # Directly connected route
    re_connected = re_prot + re_net + 'is directly connected, ' + re_interface
    # When the route length exceeds 80 chars, it is split across lines.  This is
    # the first line -- just the protocol and network.
    re_multiline = re_prot + re_net
    # This is the format seen for either a second ECMP path, or when the route has
    # been broken up across lines because of the length.
    re_ecmp = r'[ ]*' + re_metric + re_nexthop + re_lifetime + re_interface

    #Compile RegEx expressions
    reSingle = re.compile(re_single)
    reConnected = re.compile(re_connected)
    reMultiline = re.compile(re_multiline)
    reECMP = re.compile(re_ecmp)

    # Start parsing raw route table into a data structure.  Each route entry goes
    # into a dict, and all the entries are collected into a list.
    for entry in routelist:
        routeentry = {}
        regex = reSingle.match(entry)
        if regex:
            # Need to track protocol and network in case the next line is a 2nd
            # equal cost path (which doesn't show that info)
            prev_prot = regex.group('protocol') 
            prev_net = regex.group('network')
            routeentry = {  "protocol" : prev_prot,
                            "network" : prev_net,
                            "AD" : regex.group('ad'),
                            "metric" : regex.group('metric'),
                            "nexthop" : regex.group('nexthop'),
                            "lifetime" : regex.group('lifetime'),
                            "interface" : regex.group('interface')
                            }
        else:
            regex = reConnected.match(entry)
            if regex:
                routeentry = {  "protocol" : regex.group('protocol'),
                                "network" : regex.group('network'),
                                "AD" : 0,
                                "metric" : 0,
                                "nexthop" : None,
                                "interface" : regex.group('interface')
                                }
            else:
                regex = reMultiline.match(entry)
                if regex:
                    # Since this is the first line in an entry that was broken
                    # up due to length, only record protocol and network.
                    # The next line has the rest of the data needed.
                    prev_prot = regex.group('protocol') 
                    prev_net = regex.group('network')
                else:
                    regex = reECMP.match(entry)
                    if regex:
                        # Since this is a second equal cost entry, use
                        # protocol and network info from previous entry
                        routeentry = {  "protocol" : prev_prot,
                                        "network" : prev_net,
                                        "AD" : regex.group('ad'),
                                        "metric" : regex.group('metric'),
                                        "nexthop" : regex.group('nexthop'),
                                        "lifetime" : regex.group('lifetime'),
                                        "interface" : regex.group('interface')
                                        }
        if routeentry != {}:
            routetable.append(routeentry)
    return routetable


def ParseNXOSRoutes(routelist):
    '''
    This function parses the raw IOS route table into a datastucture that can 
    be used to more easily extract information.  The data structure that is 
    returned in a list of dictionaries.  Each dictionary entry represents an 
    entry in the route table and contains the following keys:
    
    {"protocol", "network", "AD", "metric", "nexthop", "lifetime", "interface"}
    
    '''

    routetable = []
    ignore_protocols = ["local", "hsrp"]
    # Various RegEx expressions to match varying parts of a route table line
    # I did it this way to break up the regex into more manageable parts, 
    # Plus some of these parts can be found in mutliple line types
    # I'm also using named groups to more easily extract the needed data.
    #
    re_via = r'^[ ]+\*?via '
    # Matches network address of route:  x.x.x.x/yy
    re_net = r'(?P<network>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d+),\W+ubest\/mbest:'
    # Matches the next hop in the route statement - "via y.y.y.y"
    re_nexthop = r'(?P<nexthop>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}),'
    # Matches outgoing interface. Not all protocols track this, so it is optional
    re_interface = r'[ ]+(?P<interface>\w+\d+(\/\d+)?),'
    # Matches the Metric and AD: i.e. [110/203213]
    re_metric = r'[ ]+\[(?P<ad>\d+)\/(?P<metric>\d+)\],'
    # Matches the lifetime of the route, usually in a format like 2m3d. Optional
    re_lifetime = r'[ ]+(?P<lifetime>[\w:]+),'
    # Protocol (letter code identifying route entry)    
    re_prot= r'[ ]+(?P<protocol>\w+(-\w+)?)[,]?'
    
    # Combining expressions above to build possible lines found in the route table
    # Standard via line from routing protocol
    re_nh_line = re_via + re_nexthop + re_interface + re_metric + re_lifetime + re_prot
    # Static routes don't have an outgoing interface.
    re_static = re_via + re_nexthop + re_metric + re_lifetime + re_prot

    #Compile RegEx expressions
    reNet = re.compile(re_net)
    reVia = re.compile(re_nh_line)
    reStatic = re.compile(re_static)

    # Start parsing raw route table into a data structure.  Each route entry goes
    # into a dict, and all the entries are collected into a list.
    for entry in routelist:
        routeentry = {}
        regex = reNet.match(entry)
        if regex:
            # Need to remember the network so the following next-hop lines
            # can be associated with the correct net in the dict.
            prev_net = regex.group('network')
        else:
            regex = reVia.match(entry)
            if regex:
                proto = regex.group('protocol')
                if proto in ignore_protocols:
                    pass
                elif proto == "direct":
                    routeentry = {  "network" : prev_net,
                                    "nexthop" : None,
                                    "interface" : regex.group('interface'),
                                    "AD" : regex.group('ad'),
                                    "metric" : regex.group('metric'),
                                    "lifetime" : regex.group('lifetime'),
                                    "protocol" : proto
                                    }
                else:
                    routeentry = {  "network" : prev_net,
                                    "nexthop" : regex.group('nexthop'),
                                    "interface" : regex.group('interface'),
                                    "AD" : regex.group('ad'),
                                    "metric" : regex.group('metric'),
                                    "lifetime" : regex.group('lifetime'),
                                    "protocol" : proto
                                    }
            else:
                regex = reStatic.match(entry)
                if regex:
                    routeentry = {  "network" : prev_net,
                                    "nexthop" : regex.group('nexthop'),
                                    "interface" : None,
                                    "AD" : regex.group('ad'),
                                    "metric" : regex.group('metric'),
                                    "lifetime" : regex.group('lifetime'),
                                    "protocol" : regex.group('protocol')
                                    }

        if routeentry != {}:
            routetable.append(routeentry)
    return routetable


#############################  UTILITY  FUNCTIONS  #############################


def alphanum_key(s):
    '''
    From http://nedbatchelder.com/blog/200712/human_sorting.html
    This function can be used as the key for a sort algorithm to give it an 
    understanding of numbers, i.e. [a1, a2, a10], instead of the default 
    (ASCII) sorting, i.e. [a1, a10, a2].
    '''

    return [int(c) if c.isdigit() else c for c in re.split('([0-9]+)', s)] 


def short_int(str):
  ''' 
  This function shortens the interface name for easier reading 
  '''
  replace_pairs = [
  ('tengigabitethernet', 'T'),
  ('gigabitethernet', 'G'),
  ('fastethernet', 'F'),
  ('ethernet', 'e'),
  ('eth', 'e'),
  ('port-channel' , 'Po')
  ]
  lower_str = str.lower()
  for pair in replace_pairs:
    if pair[0] in lower_str:
        return lower_str.replace(pair[0], pair[1])
  else:
    return str


def short_name(name):
    ''' 
    This function will remove any domain suffixes (.cisco.com) or serial 
    numbers that show up in parenthesis after the hostname of the CDP output
    '''
    #TODO: Some devices give IP address instead of name.  Need to ignore 
    #       IP format.
    #TODO: Some CatOS devices put hostname in (), instead of serial number.  
    #       Find a way to catch this when it happens.
    return name.split('.')[0].split('(')[0]


#######################  DISPLAY ERROR IF RAN DIRECTLY  #######################

def Main():
    error_str = "This is not a SecureCRT Script,\n" \
                "But a python module that holds\n" \
                "functions for other scripts to use.\n\n" \

    crt.Dialog.MessageBox(error_str, "NOT A SCRIPT", ICON_STOP)

if __name__ == "__builtin__":
    Main()