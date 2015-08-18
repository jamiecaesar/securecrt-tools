# $language = "python"
# $interface = "1.0"

# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This script will grab the detailed CDP information from a Cisco IOS or NX-OS 
# device and export it to a CSV file containing the important information, such
# as Remote Device hostname, model and IP information, in addition to the local
# and remote interfaces that connect the devices.
# 
# The path where the file is saved is specified in the "savepath" variable in
# the Main() function.
# 
# This script is tested on SecureCRT version 7.2 on OSX Mavericks

import os
import datetime
import csv
import re
import time

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
    ''' This function will remove any domain suffixes (.cisco.com) or serial numbers
    that show up in parenthesis after the hostname'''
    #TODO: Some devices give IP address instead of name.  Need to ignore IP format.
    #TODO: Some CatOS devices put hostname in (), instead of serial number.  Find a way
    #       to catch this when it happens.
    return name.split('.')[0].split('(')[0]


def CaptureOutput(command, prompt, tab):
    '''
    This function captures the raw output of the command supplied and returns it.
    The prompt variable is used to signal the end of the command output, and 
    the "tab" variable is object that specifies which tab the commands are 
    written to. 
    '''
    #Send term length command and wait for prompt to return
    tab.Send('term length 0\n')
    tab.WaitForString(prompt)
    
    # Added due to Nexus echoing twice if system hangs and hasn't printed the prompt yet.
    # Seems like maybe the previous WaitFor prompt isn't working correctly always.  Something to look into.
    time.sleep(0.1) 
    
    #Send command
    tab.Send(command + "\n")

    #Ignore the echo of the command we typed
    tab.WaitForString(command.strip())
    
    #Capture the output until we get our prompt back and write it to the file
    result = tab.ReadString(prompt)

    #Send term length back to default
    tab.Send('term length 24\n')
    tab.WaitForString(prompt)

    return result.strip("\r")

def WriteFile(raw, filename, suffix = ".txt"):
    '''
    This function simply write the contents of the "raw" variable to a 
    file with the name passed to the function.  The file suffix is .txt by
    default unless a different suffix is passed in.
    '''
    newfile = open(filename + suffix, 'wb')
    newfile.write(raw)
    newfile.close()


def ParseCDP(rawdata):
    '''
    This function parses the raw "show cdp neighbors detail" output into
    a data structure (a list of dictionaries) of only the important information,
    which can be more easily used by other functions in the program.
    '''
    def GetSeperator(raw):
        list = raw.split('\n')
        for line in list:
            if "-------" in line:
                return line
        else:
            return None
    regex = {
    "Device" : re.compile(r"Device ID:.*", re.I),
    "IP" : re.compile(r"IP\w* address:.*", re.I),
    "Platform" : re.compile(r"Platform:.*,", re.I),
    "LocalInt" : re.compile(r"Interface:.*,", re.I),
    "RemoteInt" : re.compile(r"Port ID.*:.*", re.I)
    }
    devData = []
    empty = re.compile(r"")
    sep = GetSeperator(rawdata)
    data_list = rawdata.split(sep)
    for chunk in data_list:
        devInfo = {}
        chunk = chunk.strip()
        if len(chunk) > 0:
            for name, search in regex.iteritems():
                tempsearch = search.findall(chunk)
                if len(tempsearch) > 0:
                    temp = tempsearch[0].split(":")
                else:
                    temp = ['','']                    
                devInfo[name] = temp[1].strip().strip(',')
            devData.append(devInfo)
    return devData


def CDPtoCSV(data, filename, suffix=".csv"):
    '''
    This function takes the parsed CDP data and puts it into a CSV file with
    the supplied filename.  The default suffix is .csv unless a different one 
    is passed in.
    '''
    header = ['Local Intf', 'Remote ID', 'Remote Intf', 'IP Address', 'Platform']
    newfile = open(filename + suffix, 'wb')
    csvOut = csv.writer(newfile)
    csvOut.writerow(header)
    for device in data:
        csvOut.writerow([short_int(device["LocalInt"]), short_name(device["Device"]), 
            short_int(device["RemoteInt"]), device["IP"], device["Platform"]])
    newfile.flush()
    newfile.close()


def Main():
    '''
    The purpose of this program is to capture the CDP information from the connected
    switch and ouptut it into a CSV file.
    '''
    SendCmd = "show cdp neighbors detail"

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
        filebits = [hostname, "cdp", mydate]
        filename = '-'.join(filebits)
        
        #Create path to save configuration file and open file
        fullFileName = os.path.join(os.path.expanduser('~'), savepath + filename)

        raw = CaptureOutput(SendCmd, prompt, tab)

        cdpInfo = ParseCDP(raw)
        CDPtoCSV(cdpInfo, fullFileName)

    tab.Synchronous = False
    tab.IgnoreEscape = False


Main()
