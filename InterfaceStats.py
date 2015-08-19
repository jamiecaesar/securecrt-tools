# $language = "python"
# $interface = "1.0"

# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script will scrape some stats (packets, rate, errors) from all the UP interfaces on the device
# and put it into a CSV file.  The path where the file is saved is specified in the
# "savepath" variable in the Main() function.
#


import os
import datetime
import csv
import re
import sys

savepath = 'Dropbox/SecureCRT/Backups/'
mydatestr = '%Y-%m-%d-%H-%M-%S'

def GetHostname(tab):
    '''
    This function will capture the prompt of the device.  The script will capture the
    text that is sent back from the remote device, which includes what we typed being
    echoed back to us, so we have to account for that while we parse data.
    '''
    #Send two line feeds
    tab.Send("\n\n")
    
    # Waits for first linefeed to be echoed back to us
    tab.WaitForString("\n") 
    
    # Read the text up to the next linefeed.
    prompt = tab.ReadString("\n") 

    #Remove any trailing control characters
    prompt = prompt.strip()

    # Check for non-enable mode (prompt ends with ">" instead of "#")
    if prompt[-1] == ">": 
        return None

    # Get out of config mode if that is the active mode when the script was launched
    elif "(conf" in prompt:
        tab.Send("end\n")
        hostname = prompt.split("(")[0]
        tab.WaitForString(hostname + "#")
        # Return the hostname (everything before the first "(")
        return hostname
        
    # Else, Return the hostname (all of the prompt except the last character)        
    else:
        return prompt[:-1]


def WriteOutput(command, filename, prompt, tab):
    '''
    This function captures the raw output of the command supplied and returns it.
    The prompt variable is used to signal the end of the command output, and 
    the "tab" variable is object that specifies which tab the commands are 
    written to. 
    '''
    endings=["\r\n", prompt]
    newfile = open(filename, 'wb')

    # Send term length command and wait for prompt to return
    tab.Send('term length 0\n')
    tab.WaitForString(prompt)
    
    # Send command
    tab.Send(command + "\n")

    # Ignore the echo of the command we typed (including linefeed)
    tab.WaitForString(command.strip())

    # Loop to capture every line of the command.  If we get CRLF (first entry
    # in our "endings" list), then write that line to the file.  If we get
    # our prompt back (which won't have CRLF), break the loop b/c we found the
    # end of the output.
    while True:
        nextline = tab.ReadString(endings)
        # If the match was the 1st index in the endings list -> \r\n
        if tab.MatchIndex == 1:
            # For Nexus will have extra "\r"s in it, leading to extra lines at the
            # start of the file.  Don't write those.
            if nextline != "\r":
                # Write the line of text to the file
                # crt.Dialog.MessageBox("Original:" + repr(nextline) + "\nStripped:" + repr(nextline.strip('\r')))
                newfile.write(nextline.strip("\r") + "\r\n")
        else:
            # We got our prompt (MatchIndex is 2), so break the loop
            break
    
    newfile.close()
    
    # Send term length back to default
    tab.Send('term length 24\n')
    tab.WaitForString(prompt)


def ParseRawIntfs(raw_int_output):
    '''
    This function parses the raw show interface output into a datastucture that can be used 
    to more easily extract information.  The data structure that is returned in a list of 
    dictionaries.
    '''
    intftable = []
    # Various RegEx expressions to match varying parts of a show int line
    # I did it this way to break up the regex into more manageable parts, 
    # Plus some of these parts can be found in multiple line types
    # I'm also using named groups to more easily extract the needed data.
    #
    # Interface Name (only capture interfaces that are up)
    re_intf = r'(?P<Interface>[\w\/\.-]*) is up, line protocol is up'
    re_desc = r'.*Description: (?P<desc>.*)' 
    re_inrate = r'.*input rate (?P<InBPS>\d*) bits\/sec, (?P<InPPS>\d*) packets\/sec'
    re_outrate = r'.*output rate (?P<OutBPS>\d*) bits\/sec, (?P<OutPPS>\d*) packets\/sec'
    re_inpkts = r'\W*(?P<InPackets>\d*) packets input.*'
    re_inerr = r'\W*(?P<InputErr>\d*) input errors,'
    re_outpkts = r'\W*(?P<OutPackets>\d*) packets output.*'
    re_outerr = r'\W*(?P<OutputErr>\d*) output errors,'

    #Compile RegEx expressions
    reIntf = re.compile(re_intf)
    reDesc = re.compile(re_desc)
    reInRate = re.compile(re_inrate)
    reOutRate = re.compile(re_outrate)
    reInPkts = re.compile(re_inpkts)
    reInErr = re.compile(re_inerr)
    reOutPkts = re.compile(re_outpkts)
    reOutErr = re.compile(re_outerr)

    # Start parsing raw interface output into a data structure.  Each int entry goes
    # into a dict, and all the entries are collected into a list.
    intfentry = {   "Interface" : None,
                    "Description" : None,
                    "InBPS" : None,
                    "InPPS" : None,
                    "OutBPS" : None,
                    "OutPPS" : None,
                    "InputPackets" : None,
                    "InputErr" : None,
                    "OutputPackets" : None,
                    "OutputErr" : None
                }
    for line in raw_int_output:
        # Check if this is the start of a new interface block
        line = line.strip()
        regex = reIntf.match(line)
        if regex:
            # If so, write the previous block and reset
            if intfentry['Interface'] is not None:
                intftable.append(intfentry)
                intfentry = {   "Interface" : regex.group('Interface'),
                                "Description" : None,
                                "InBPS" : None,
                                "InPPS" : None,
                                "OutBPS" : None,
                                "OutPPS" : None,
                                "InputPackets" : None,
                                "InputErr" : None,
                                "OutputPackets" : None,
                                "OutputErr" : None
                            }
            else:
                # If so, but the current intfentry doesn't have an interface name assigned yet
                intfentry['Interface'] = regex.group('Interface')
        
        elif "Description" in line:
            regex = reDesc.match(line)
            if regex:
                intfentry['Description'] = regex.group('desc')
        elif intfentry['InBPS'] is None:
            regex = reInRate.match(line)
            if regex:
                intfentry['InBPS'] = regex.group('InBPS')
                intfentry['InPPS'] = regex.group('InPPS')
        elif intfentry['OutBPS'] is None:
            regex = reOutRate.match(line)
            if regex:
                intfentry['OutBPS'] = regex.group('OutBPS')
                intfentry['OutPPS'] = regex.group('OutPPS')
        elif intfentry['InputPackets'] is None:
            regex = reInPkts.match(line)
            if regex:
                intfentry['InputPackets'] = regex.group('InPackets')  
        elif intfentry['InputErr'] is None:
            regex = reInErr.match(line)
            if regex:
                intfentry['InputErr'] = regex.group('InputErr')
        elif intfentry['OutputPackets'] is None:
            regex = reOutPkts.match(line)
            if regex:
                intfentry['OutputPackets'] = regex.group('OutPackets')  
        elif intfentry['OutputErr'] is None:
            regex = reOutErr.match(line)
            if regex:
                intfentry['OutputErr'] = regex.group('OutputErr')
    # If we reached the end, write the final entry
    if intfentry['Interface'] is not None:
        intftable.append(intfentry) 
    return intftable


def DictListToCSV(data, filename, suffix=".csv"):
    '''
    This function takes a list and puts it into a CSV file with the supplied 
    filename.  The default suffix is .csv unless a different one is passed in.
    '''
    with open(filename + suffix, 'wb') as csvfile:
        field_names =   [ "Interface", "Description", "InBPS", "InPPS", "OutBPS", "OutPPS", 
                          "InputPackets", "InputErr", "OutputPackets", "OutputErr"
                        ]
        writer = csv.DictWriter(csvfile, fieldnames=field_names)
        writer.writerow(dict(zip(writer.fieldnames, writer.fieldnames)))
        for entry in data:
            writer.writerow(entry)


def Main():
    SendCmd = "show interfaces"

    #Create a "Tab" object, so that all the output goes into the correct Tab.
    objTab = crt.GetScriptTab()
    tab = objTab.Screen  #Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"
    tab.Synchronous = True
    tab.IgnoreEscape = True

    #Get the prompt of the device
    hostname = GetHostname(tab)
    prompt = hostname + "#"

    if hostname == None:
        crt.Dialog.MessageBox("Either not in enable mode, or the prompt could not be detected")
    else:
        now = datetime.datetime.now()
        mydate = now.strftime(mydatestr)
        
        #Create Filename
        filebits = [hostname, "int_summary", mydate]
        filename = '-'.join(filebits)
        
        #Create path to save configuration file and open file
        fullFileName = os.path.join(os.path.expanduser('~'), savepath + filename)
        rawIntfFile = fullFileName + ".txt"

        # Save raw "show ip route" output to a file.  Dumping directly to a var has problems when the
        # route table is very large (1000+ lines)
        WriteOutput(SendCmd, rawIntfFile, prompt, tab)

        # Create a list that contains all the route entries (minus their line endings)
        intf_raw = [line.rstrip('\n') for line in open(rawIntfFile)]
        
        os.remove(rawIntfFile)
        
        summarytable = ParseRawIntfs(intf_raw)
        DictListToCSV(summarytable, fullFileName)

    tab.Synchronous = False
    tab.IgnoreEscape = False


Main()
