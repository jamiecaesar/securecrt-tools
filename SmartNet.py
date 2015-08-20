#$language = "python"
#$interface = "1.0"

# SmartNet.py
# 
# Description:
#   Connects to all sessions in a folder, and all sub folders, and
#   runs the basic inventory and version commands needed for SmartNet
#
#   The results of each command are captured into a variable, and then
#   written to an individual log file (one log file for each command).
# 
#   Filename format is:
#   ~/$savepath/<Host Name>-<Command Name>-<Date Format>.txt

import os
import datetime
import sys


# Adjust these to your environment
savepath = 'SmartNet/'
mydatestr = '%Y-%m-%d-%H-%M-%S'
my_session_dir = "~/VanDyke/Config/Sessions/"
# site dir must end with / if you use them.
#my_site_dir = "Site1/"
my_site_dir = ""


COMMANDS = [
  "show inventory",
  "show hardware",
  "show hardware inventory",
  "show version",
  ]

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


def GetSessions(Session_Dir,Site_Dir):
  '''
  This function will get all the session names in a starting directory and all
  subdirectories.
  '''
  # Files in Session directories to ignore
  blacklist = [ "__FolderData__.ini" ]
  
  # Extention of all Session files in .ini so we'll only look for those
  extension = ".ini"
  
  # Get list of Sessions
  SessionList = []
  Root_Dir = Session_Dir + Site_Dir
  for root, dirs, files in os.walk(Root_Dir):
    for file in files:
      if file.endswith(extension):
        if not file in blacklist:
          if dirs:
            session_name = Site_Dir + str(dirs) + (os.path.splitext(file)[0])
          else:
            session_name = Site_Dir + (os.path.splitext(file)[0])
          SessionList.append(session_name)
              
  return SessionList


def CaptureOutput(command, prompt, tab):
  '''
  This function captures the raw output of the command supplied and returns it.
  The prompt variable is used to signal the end of the command output, and 
  the "tab" variable is object that specifies which tab the commands are 
  written to. 
  '''
  #Send two line feeds
  #Helps with timing on Nexus platforms for comman separation
  tab.Send("\n\n")
  tab.WaitForString(prompt)
  #Send command
  tab.Send(command)

  #Ignore the echo of the command we typed
  tab.WaitForString(command.strip())
    
  #Capture the output until we get our prompt back and write it to the file
  result = tab.ReadString(prompt)

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


def main():

  errorMessages = ""
  
  # Get Sessions
  sessionsArray = GetSessions(my_session_dir, my_site_dir)

  # Connect to each session and issue a few commands, then disconnect.
  for session in sessionsArray:
    try:
      crt.Session.Connect("/S \"" + session + "\"")
    except ScriptError:
      error = crt.GetLastErrorMessage()

    # If we successfully connected, we'll do the work we intend to do...
    # otherwise, we'll skip the work and move on to the next session in 
    # the list.
    if crt.Session.Connected:

      crt.Sleep(1000)
      #Create a "Tab" object, so that all the output goes into the correct Tab.
      objTab = crt.GetScriptTab()
      tab = objTab.Screen  #Allows us to type "tab.xxx" instead of "objTab.Screen.xxx"
      tab.IgnoreEscape = True
      tab.Synchronous = True
      
      #Get the prompt of the device
      hostname = GetHostname(tab)
        
      if hostname == None:
        crt.Dialog.MessageBox("You must be in enable mode to run this script.")
      else:
        prompt = hostname + "#"
        
        now = datetime.datetime.now()
        mydate = now.strftime(mydatestr)
    
        #Send term length command and wait for prompt to return
        tab.Send('term length 0\n')
        tab.Send('term width 0\n')
        tab.WaitForString(prompt)
        
        for (index, SendCmd) in enumerate(COMMANDS):
          SendCmd = SendCmd.strip()
          # Save command without spaces to use in output filename.
          CmdName = SendCmd.replace(" ", "_")
          # Add a newline to command before sending it to the remote device.
          SendCmd = SendCmd + "\n"
        
          #Create Filename
          hostip = crt.Session.RemoteAddress
          filehostip = hostip.replace(".", "_")
          filehostname = hostname.replace("/", "-")
          filehostname = hostname.replace("\\", "-")
          filebits = [hostname, filehostip, CmdName, mydate + ".txt"]
          filename = '-'.join(filebits)
          
          #Create path to save configuration file and open file
          fullFileName = os.path.join(os.path.expanduser('~'), savepath + filename)
          
          CmdResult = CaptureOutput(SendCmd, prompt, tab)
          if "% Invalid " not in CmdResult:
            WriteFile(CmdResult, fullFileName)
          
        tab.Send('exit\n')

        tab.Synchronous = False
        tab.IgnoreEscape = False
        
        # Now disconnect from the remote machine...
        crt.Session.Disconnect()
        # Wait for the connection to close
        while crt.Session.Connected == True:
          crt.Sleep(100)

        crt.Sleep(1000)
    else:
        errorMessages = errorMessages + "\n" + "*** Error connecting to " + session + ": " + error

  if errorMessages == "":
    crt.Dialog.MessageBox("Tasks completed.  No Errors were detected.")
  else:
    crt.Dialog.MessageBox("Tasks completed.  The following errors occurred:\n" + errorMessages)

main()