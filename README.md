SecureCRT Scripts
==================
SecureCRT Python scripts for doing various tasks on Cisco equipment.

These have been testing using SecureCRT 7.x on OSX (10.9 and 10.10), as well as Windows 8.1.

**Before using, you will need to modify the `savepath` variable to reference a valid output directory for your particular machine.**

Scripts:
========
* SaveRunning.py - Captures the running config to a file, named based on the prompt and current date.
* SaveCDPasCSV.py - Captures CDP information and saves the important info (interfaces, remote device, IP address) to a CSV file
* SaveOutput.py - Generic script that prompts for a command and saves that output to a file.
* NextHopSummary.py - Outputs a CSV file with all the next hops and a detailed breakdown of each type of route pointing at that next hop.  *Currently IOS Only*
* Prefix_no.py - Script that will capture the highlighted text and send those commands to the device with a prepended "no ".  If the command starts with "no ", it will remove it before sending.
* Document_Device.py - A script that will issue a list of commands to the connected device and save valid output to individual files per command.
