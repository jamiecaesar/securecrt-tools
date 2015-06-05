#$language = "python"
#$interface = "1.0"


import os
import subprocess
import datetime
import sys

SCRIPT_TAB = crt.GetScriptTab()

TAB_NAME = SCRIPT_TAB.Caption

COMMANDS = [
	"show ip interface brief",
	"show ipv6 interface brief",
	"show cdp neighbors",
	"show cdp neighbors detail",
	"show running",
	"show inventory",
	"show version",
	"show ip route",
	"show ip protocols",
	"show ipv6 protocols",
	"show ip ospf neighbor",
	"show ip eigrp neighbor",
	"show ipv6 route",
	"show ipv6 protocols",
	"show controllers E1",
	"show dial-peer voice summary",
	"show call active voice brief",
	"show cann history voice brief",
	"show spanning-tree",
	"show vtp status",
	"show etherchannel sum",
	"show crypto isakmp sa",
	"show crypto ipsec sa",
	"show crypto map",
	"show access-list",
	"show policy-map",
	"show policy-map interface"
	"show route-map",
	"show cdp neighbors detail",
	"show log",
	"show debug",
	"write"
	]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
	SCRIPT_TAB.Screen.IgnoreEscape = True
	SCRIPT_TAB.Screen.Synchronous = True
	
	# Make sure we are connected
	if not SCRIPT_TAB.Session.Connected:
		crt.Dialog.MessageBox(
			"Not Connected.  Please connect before running this script.")
		return
	
	# Find logging directory & setup file path parts
	logfile = SCRIPT_TAB.Session.LogFileName
	logdir = os.path.dirname(logfile)
	Today = str(datetime.date.today().isoformat()) 

	# Complain if logging isnt currently enabled, Else Setup the file path
	if logfile == "" :
		crt.Dialog.MessageBox("Error.\n\n\
		This script requires a session configuration in which a\
		log file is defined.\n\n\
		Specify a Log file name in Session Options, ""Terminal\
		Log File"", and run this script again.")
	else:
		logFileName = logdir + os.sep + Today + "-" + TAB_NAME + "-Backup.txt"
	


	# Hold off until cursor has been still for 1 second
	while True:
		if not SCRIPT_TAB.Screen.WaitForCursor(1):
			break
	rowIndex = SCRIPT_TAB.Screen.CurrentRow
	colIndex = SCRIPT_TAB.Screen.CurrentColumn - 1

	# Grab prompt
	prompt = SCRIPT_TAB.Screen.Get(rowIndex, 0, rowIndex, colIndex)
	prompt = prompt.strip()


	# If we are in config mode, drop to exec	
	if "config" in prompt == 1:
		SCRIPT_TAB.Screen.Send("end" + '\r')
	
	# Set terminal legth to 0
	SCRIPT_TAB.Screen.Send("terminal length 0" + '\r')
	


	# Set log file and open it 
	filep = open(logFileName, 'wb+')

	# Loop through commands, printing as we go
	for (i, command) in enumerate(COMMANDS):
		command = command.strip()
		prev_command = i - 1
		
		# Send the command text to the remote
		SCRIPT_TAB.Screen.Send(COMMANDS[i] + '\r')

		# Wait for the command to be echo'd back to us.
		SCRIPT_TAB.Screen.WaitForString('\r', 1)
		SCRIPT_TAB.Screen.WaitForString('\n', 1)

		result = SCRIPT_TAB.Screen.ReadString(prompt)
		result = result.strip()
		
		# Log only commands supported by the device
		if "% Invalid input" not in result:
			filep.write(os.linesep)
			filep.write("#################### " + COMMANDS[prev_command] + " ####################" + os.linesep)
			filep.write(os.linesep)
				
		
			# Write out the results of the command to our log file
			filep.write(result + os.linesep)

	
	# Close the log file
	filep.close()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

main()
