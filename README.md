SecureCRT Scripts
==================
SecureCRT Python scripts for doing various tasks on Cisco equipment.

These scripts have been testing with SecureCRT 7.x on multiple machines of varying operating systems (OSX 10.9, 10.10.  Windows 7, 8.1).  If you find that a script won't work on your machine, please post an issue to let us know!

**NOTE**: These scripts have been recently refactored to use a shared module called `ciscolib.py`.  The majority of the functions that all of these scripts used are stored in that file.  That means at a minimum you need the script and the `ciscolib.py` file for the script to run (and in the same directory).   If you clone the entire repository you shouldn't need to worry about this.

**Before using, you will need to modify the "Settings" section of the scripts to reference a valid output directory for your particular machine.**

Scripts:
========
* ConfigLoad.py - A script that will load a config file to a cisco device and mark any errors
* Document_Device.py - A script that will run a list of commands on the connected device, saving each command output into an individual file.  All outputs are saved into a folder based on the device's hostname.
* InterfaceStats.py - Outputs a CSV file for a quick and easy view of some high level details about all interfaces that are "up", such as total packets in/out, packet rate in/out and errors in/out.
* IntStatsOverTime.py - Outputs a CSV file with interface statistics over a configurable time period for each interface that is "up".  Allows easy graph creation by opening the file in Excel, highlighting the data and inserting a graph object.
* NextHopSummary.py - Outputs a CSV file with all the next hops and a detailed breakdown of each type of route pointing at that next hop.
* SaveRunning.py - Captures the running config to a file, named based on the prompt and current date.
* SaveCDPtoCSV.py - Captures CDP information and saves the important info (interfaces, remote device, IP address) to a CSV file
* SaveMACtoCSV.py - Captures the MAC table and saves the VLAN, MAC and Interface to a CSV file.
* SaveOutput.py - Generic script that prompts for a command and saves that output to a file.
* ToggleNo.py - Script that will capture the highlighted text and send those commands to the device with a prepended "no ".  If the command starts with "no ", it will remove it before sending.
* UsedVLANs.py - A script that will output a CSV file with a list of VLANs that have ports assigned to them from the switch.  Settings in the script allow for changing the behavior to list all VLANs with their associated count.
