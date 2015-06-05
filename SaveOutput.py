# $language = "python"
# $interface = "1.0"

# Author: Jamie Caesar
# Twitter: @j_cae
# 
# This SecureCRT script will prompt the user for a command to a Cisco IOS or NX-OS 
# device and dump the output to a file.  The path where the file is saved is
# specified in the "savepath" variable in the Main() function.
#
# This script is tested on SecureCRT version 7.2 on OSX Mavericks
#


import os
import datetime

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
    tab.Send(command)

    #Ignore the echo of the command we typed
    tab.WaitForString(command.strip())
    
    #Capture the output until we get our prompt back and write it to the file
    result = tab.ReadString(prompt)

    #Send term length back to default
    tab.Send('term length 24\n')
    tab.WaitForString(prompt)

    return result

def WriteFile(raw, filename):
    '''
    This function simply write the contents of the "raw" variable to a 
    file with the name passed to the function.  The file suffix is .txt by
    default unless a different suffix is passed in.
    '''
    newfile = open(filename, 'wb')
    newfile.write(raw)
    newfile.close()


def Main():
    '''
    This purpose of this program is to capture the output of the command entered by the
    user and save it to a file.  This method is much faster than manually setting a log
    file, or trying to extract only the information needed from the saved log file.
    '''
    SendCmd = crt.Dialog.Prompt("Enter the command to capture")
    if SendCmd == "":
        return
    else:
        # Save command without spaces to use in output filename.
        CmdName = SendCmd.replace(" ", "_")
        # Add a newline to command before sending it to the remote device.
        SendCmd = SendCmd + "\r\n"

    #Create a "Tab" object, so that all the output goes into the correct Tab.
    objTab = crt.GetScriptTab()
    tab = objTab.Screen  #Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"
    tab.Synchronous = True
    tab.IgnoreEscape = True

    #Get the prompt of the device
    hostname = GetHostname(tab)
    
    if hostname == None:
        crt.Dialog.MessageBox("You must be in enable mode to run this script.")
    else:
        prompt = hostname + "#"

        now = datetime.datetime.now()
        mydate = now.strftime(mydatestr)
        
        #Create Filename
        filebits = [hostname, CmdName, mydate + ".txt"]
        filename = '-'.join(filebits)
        
        #Create path to save configuration file and open file
        fullFileName = os.path.join(os.path.expanduser('~'), savepath + filename)

        WriteFile(CaptureOutput(SendCmd, prompt, tab), fullFileName)

    tab.Synchronous = False
    tab.IgnoreEscape = False

Main()
