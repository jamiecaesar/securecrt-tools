# $language = "python"
# $interface = "1.0"

import os
import datetime

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

def GetDate():
    '''
    This function returns a tuple of the year, month and day.
    '''
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
    This purpose of this program is to capture the output of the "show run" command and
    save it to a file.  This method is much faster than manually setting a log file, or 
    trying to extract the information from a log file.
    '''
    SendCmd = "show run\n"
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
        filebits = [hostname, "config", year, month, day + ".txt"]
        filename = '-'.join(filebits)
        
        #Create path to save configuration file and open file
        fullFileName = os.path.join(os.environ['HOME'], savepath + filename)

        WriteFile(CaptureOutput(SendCmd, prompt, tab), fullFileName)

    tab.Synchronous = False



Main()
