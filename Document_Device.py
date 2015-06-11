#$language = "python"
#$interface = "1.0"

# Document_Device.py
# 
# Description:
#   Sends a series of Cisco Show commands one by one as listed in the
#   COMMANDS array.  The results of each command are captured into a
#   variable, and then written to an individual log file (one log file
#   for each command).
# 
#   Filename format is:
#   ~/$savepath/<Host Name>/<Command Name>-<Host Name>-<Date Format>.txt

import os
import subprocess
import datetime
import sys

# Adjust these to your environment
savepath = 'Dropbox/SecureCRT/Backups/'
mydatestr = '%Y-%m-%d-%H-%M-%S'

# Be careful when adding to this list.  If you forget a "," then those two
# commands will run together.
COMMANDS = [
    "show call active voice brief",
    "show call history voice brief",
    "show cdp neighbors detail",
    "show cdp neighbors",
    "show clock",
    "show controllers E1",
    "show controllers T1",
    "show crypto ipsec sa",
    "show crypto isakmp sa",
    "show crypto map",
    "show debug",
    "show dial-peer voice summary",
    "show environment power",
    "show etherchannel summary",
    "show interface counters error",
    "show interface description",
    "show interface stats",
    "show interface status",
    "show interface summary",
    "show interface transceiver detail",
    "show interface transceiver",
    "show interfaces",
    "show inventory",
    "show ip access-list",
    "show ip arp",
    "show ip bgp",
    "show ip bgp summary",
    "show ip eigrp neighbor",
    "show ip interface brief",
    "show ip ospf neighbor",
    "show ip protocols",
    "show ip route 0.0.0.0",
    "show ip route",
    "show ipv6 interface brief",
    "show ipv6 protocols",
    "show ipv6 protocols",
    "show ipv6 route",
    "show log",
    "show mac address-table dynamic",
    "show mac address-table",
    "show module",
    "show policy-map interface",
    "show policy-map",
    "show port-channel summary",
    "show power",
    "show route-map",
    "show running",
    "show spanning-tree",
    "show spanning-tree root",
    "show standby brief",
    "show switch detail",
    "show version",
    "show vlan",
    "show vtp status"
    ]

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
    tab.Send(command)

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


def Main():

    # Create a "Tab" object, so that all the output goes into the correct Tab.
    objTab = crt.GetScriptTab()
    # Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"
    tab = objTab.Screen  
    tab.IgnoreEscape = True
    tab.Synchronous = True
        
    # Get the prompt of the device
    hostname = GetHostname(tab)
        
    if hostname == None:
        crt.Dialog.MessageBox("You must be in enable mode to run this script.")
    else:
        prompt = hostname + "#"
        
        now = datetime.datetime.now()
        mydate = now.strftime(mydatestr)

        for (index, SendCmd) in enumerate(COMMANDS):
            SendCmd = SendCmd.strip()
            # Save command without spaces to use in output filename.
            CmdName = SendCmd.replace(" ", "_")
            # Add a newline to command before sending it to the remote device.
            SendCmd = SendCmd + "\n"
        
            # Create Filename
            filebits = [CmdName, hostname, mydate + ".txt"]
            filename = '-'.join(filebits)
            
            # Create path to save configuration file and open file
            fullDirectory = os.path.join(os.path.expanduser('~'), savepath, hostname)
            if not os.path.isdir(fullDirectory):
                os.mkdir(fullDirectory) 
            fullFileName = os.path.join(fullDirectory, filename)
            
            # Write the output of the command to a file.
            WriteOutput(SendCmd, fullFileName, prompt, tab)
            
            # If file isn't empty (greater than 3 bytes)
            # Some of these file only save one CRLF, and so we can't match on 0 bytes
            if os.path.getsize(fullFileName) > 3: 
                # Open the file we just created.
                newfile = open(fullFileName, "r")

                # If the file only contains invalid command error, delete it.
                for line in newfile:
                    if "% Invalid" in line:
                        newfile.close()
                        os.remove(fullFileName)
                        break 
                else:
                    newfile.close()
            # If the file is empty, delete it
            else:
                os.remove(fullFileName)
            
    tab.Synchronous = False
    tab.IgnoreEscape = False
        
    crt.Dialog.MessageBox("Device Documentation Script Complete", "Script Complete", 0)


Main()
