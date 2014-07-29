# $language = "python"
# $interface = "1.0"

# This script is designed to capture information from Cisco routers and switches.

import os
import datetime
import csv
import re

def GetHostname(tab):
    '''
    This function will capture the prompt of the device.  The script will capture the
    text that is sent back from the remote device, which includes what we typed being
    echoed back to us, so we have to account for that while we parse data.
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
    return name.split('.')[0].split('(')[0]


def CaptureOutput(command, prompt, tab):
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
    #Get Date
    now = datetime.datetime.now()
    day = str(now.day)
    month = str(now.month)
    year = str(now.year)
    
    #Prepend '0' to day and month if only a single digit (better for alpha sorting)
    if len(day) == 1:
        day = '0' + day
    if len(month) == 1:
        month = '0' + month

    return year, month, day


def WriteFile(raw, filename, suffix = ".txt"):
    newfile = open(filename + suffix, 'wb')
    newfile.write(raw)
    newfile.close()


def ParseCDP(rawdata):
    def GetSeperator(raw):
        list = raw.split('\n')
        for line in list:
            if "-------" in line:
                return line
        else:
            return None
    regex = {
    "Device" : re.compile(r"Device ID:.*"),
    "IP" : re.compile(r"IP address:.*"),
    "Platform" : re.compile(r"Platform:.*,"),
    "LocalInt" : re.compile(r"Interface:.*,"),
    "RemoteInt" : re.compile(r"Port ID.*:.*")
    }
    devData = []
    sep = GetSeperator(rawdata)
    data_list = rawdata.split(sep)
    data_list.remove(u'\r\n')
    for chunk in data_list:
        devInfo = {}
        for name, search in regex.iteritems():
            temp = search.findall(chunk)[0].split(":")
            devInfo[name] = temp[1].strip().strip(',')
        devData.append(devInfo)
    return devData


def CDPtoCSV(data, filename, suffix=".csv"):
    header = ['Local Intf', 'Remote ID', 'Remote Intf', 'IP Address', 'Platform']
    newfile = open(filename + suffix, 'wb')
    csvOut = csv.writer(newfile)
    csvOut.writerow(header)
    for device in data:
        csvOut.writerow([short_int(device["LocalInt"]), short_name(device["Device"]), 
            short_int(device["RemoteInt"]), device["IP"], device["Platform"]])
    newfile.close()


def Main():
    SendCmd = "show cdp neighbors detail"
    savepath = 'Dropbox/SecureCRT/Backups/'

    #Create a "Tab" object, so that all the output goes into the correct Tab.
    objTab = crt.GetScriptTab()
    objTab.Screen.Synchronous = True
    tab = objTab.Screen  #Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"

    #Get the prompt of the device
    hostname = GetHostname(tab)

    if hostname == None:
        crt.Dialog.MessageBox("Either not in enable mode, or the prompt could not be detected")
        tab.WaitForString(prompt.strip())
    else:
        prompt = hostname + "#"
        #crt.Dialog.MessageBox("'" + hostname + "'")
       
        year, month, day = GetDate()
        
        #Create Filename
        filebits = [hostname, "cdp", year, month, day]
        filename = '-'.join(filebits)
        
        #Create path to save configuration file and open file
        fullFileName = os.path.join(os.environ['HOME'], savepath + filename)

        raw = CaptureOutput(SendCmd, prompt, tab)
        #WriteFile(raw, fullFileName)

        cdpInfo = ParseCDP(raw)
        #WriteFile (str(cdpInfo),fullFileName)
        CDPtoCSV(cdpInfo, fullFileName)

    tab.Synchronous = False


Main()
