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

def GetHostname(tab):
    '''
    This function will capture the prompt of the device, by capturing the text
    returned after sending a couple line feeds.  Because the script will keep
    running commands before the commands we send are echo'd back to us, we
    have to add some "WaitForString"s so we capture only what we want.
    '''
    #Send two line feeds
    tab.Send("\n\n")
    tab.WaitForString("\n") # Waits for first linefeed to be echoed back to us
    prompt = tab.ReadString("\n") #Read the text up to the next linefeed.
    prompt = prompt.strip() #Remove any trailing control characters
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
    
    #Send command
    tab.Send(command + "\n")

    #Ignore the echo of the command we typed
    tab.WaitForString(command)
    
    #Capture the output until we get our prompt back and write it to the file
    result = tab.ReadString(prompt)

    #Send term length back to default
    tab.Send('term length 24\n')
    tab.WaitForString(prompt)

    return result

def GetDate():
    '''
    This function returns a tuple of the year, month and day.
    '''
    #Get Date
    now = datetime.datetime.now()
    day = str(now.day)
    month = str(now.month)
    year = str(now.year)
    
    #Prepend '0' to single-digit day and month (better for alpha sorting of filenames)
    if len(day) == 1:
        day = '0' + day
    if len(month) == 1:
        month = '0' + month

    return year, month, day


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
    # 'savepath' can be either a relative path from HOME, or an absolute path.  Both
    # will work.
    savepath = 'Dropbox/SecureCRT/Backups/'

    #Create a "Tab" object, so that all the output goes into the correct Tab.
    objTab = crt.GetScriptTab()
    objTab.Screen.Synchronous = True
    tab = objTab.Screen  #Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"

    #Get the prompt of the device
    hostname = GetHostname(tab)
    prompt = hostname + "#"

    if hostname == None:
        crt.Dialog.MessageBox("Either not in enable mode, or the prompt could not be detected")
    else:
        year, month, day = GetDate()
        
        #Create Filename
        filebits = [hostname, "cdp", year, month, day]
        filename = '-'.join(filebits)
        
        #Create path to save configuration file and open file
        fullFileName = os.path.join(os.environ['HOME'], savepath + filename)

        raw = CaptureOutput(SendCmd, prompt, tab)

        cdpInfo = ParseCDP(raw)
        CDPtoCSV(cdpInfo, fullFileName)

    tab.Synchronous = False


Main()
