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
#   ~/$savepath/<Host Name>-<Command Name>-<Date Format>.txt

import os
import subprocess
import datetime
import sys

# Adjust these to your environment
savepath = 'Configs/'
mydatestr = '%Y-%m-%d-%H-%M-%S'

COMMANDS = [
	"show access-list",
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
	"show environment power"
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
	"show ip arp",
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
	"show policy-map interface"
	"show policy-map",
	"show port-channel summary",
	"show power",
	"show route-map",
	"show running",
	"show spanning-tree",
	"show version",
	"show vtp status",
	"write"
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

def CaptureOutput(command, prompt, tab):
	'''
	This function captures the raw output of the command supplied and returns it.
	The prompt variable is used to signal the end of the command output, and 
	the "tab" variable is object that specifies which tab the commands are 
	written to. 
	'''
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
			filebits = [hostname, CmdName, mydate + ".txt"]
			filename = '-'.join(filebits)
			
			#Create path to save configuration file and open file
			fullFileName = os.path.join(os.path.expanduser('~'), savepath + filename)
			
			CmdResult = CaptureOutput(SendCmd, prompt, tab)
			if "% Invalid input" not in CmdResult:
				WriteFile(CmdResult, fullFileName)
			
			CmdResult = ''
			
		#Send term length back to default
		tab.Send('term length 24\n')
		tab.Send('term width 80\n')
		tab.WaitForString(prompt)

		tab.Synchronous = False
		tab.IgnoreEscape = False
		
	crt.Dialog.MessageBox("Device Documentation Script Complete", "Script Complete", 0)

main()
