#$language = "python"
#$interface = "1.0"

################################  SCRIPT INFO  ################################
# Document_Device.py
# 
# Description:
#   Sends a series of Cisco Show commands one by one as listed in the
#   COMMANDS array.  The results of each command are captured into a
#   variable, and then written to an individual log file (one log file
#   for each command).
# 


settings = {}
###############################  SCRIPT SETTING  ###############################
#### WHERE TO SAVE FILES:
# Enter the path to the directory where the script output should be stored.
# This can either be a relative path (which will start in the user's home
#   directory) or an absolute path (i.e. C:\Output or /Users/Jamie/Output).
settings['savepath'] = 'Dropbox/SecureCRT/Output/'
# The script will use the correct variable based on which OS is running.
#
#
#### FILENAME FORMAT
# Choose the format of the date string added to filenames created by this script.
# Example = '%Y-%m-%d-%H-%M-%S'
# See the bottom of https://docs.python.org/2/library/datetime.html for all 
# available directives that can be used.
settings['date_format'] = '%Y-%m-%d-%H-%M-%S'
###############################  END OF SETTINGS ###############################


# Import OS and Sys module to be able to perform required operations for adding
# the script directory to the python path (for loading modules), and manipulating
# paths for saving files.
import os
import sys

# Add the script directory to the python path (if not there) so we can import 
# modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Imports from Cisco SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import GetDateString
from ciscolib import GetAbsolutePath
from ciscolib import WriteOutput


# Be careful when adding to this list.  If you forget a "," then those two
# commands will run together.  The last entry must not have a comma after it, 
# which might happen if you comment out the last line.
COMMANDS = [
    # "show call active voice brief",
    # "show call history voice brief",
    # "show cdp neighbors detail",
    "show cdp neighbors",
    # "show clock",
    # "show controllers E1",
    # "show controllers T1",
    # "show crypto ipsec sa",
    # "show crypto isakmp sa",
    # "show crypto map",
    # "show debug",
    # "show dial-peer voice summary",
    "show environment power",
    "show etherchannel summary",
    # "show interface counters error",
    # "show interface description",
    # "show interface stats",
    "show interface status",
    # "show interface summary",
    # "show interface transceiver detail",
    # "show interface transceiver",
    # "show interfaces",
    "show inventory",
    # "show ip access-list",
    # "show ip arp",
    # "show ip bgp",
    # "show ip bgp summary",
    "show ip eigrp neighbor",
    "show ip interface brief | ex una",
    # "show ip ospf neighbor",
    # "show ip protocols",
    # "show ip route 0.0.0.0",
    "show ip route",
    # "show ipv6 interface brief",
    # "show ipv6 protocols",
    # "show ipv6 protocols",
    # "show ipv6 route",
    "show license",
    "show license udi",
    # "show log",
    "show mac address-table dynamic",
    # "show mac address-table",
    # "show module",
    # "show policy-map interface",
    # "show policy-map",
    # "show port-channel summary",
    # "show power",
    # "show route-map",
    "show running",
    "show spanning-tree",
    "show spanning-tree root",
    # "show standby brief",
    "show stack-power",
    "show switch detail",
    "show version",
    "show vlan",
    "show vtp status"
    ]


def Main():

    # Run session start commands and save session information into a dictionary
    session = StartSession(crt)

    # Extract the hostname from the session info.
    hostname = session['hostname']
    save_path = os.path.join(settings['savepath'], hostname)

    # Get the current date in the format supplied in date_format
    mydate = GetDateString(settings['date_format'])

    # Iterate through each command and write a file with the output.
    for (index, SendCmd) in enumerate(COMMANDS):
        SendCmd = SendCmd.strip()
        # Save command without spaces to use in output filename.
        CmdName = SendCmd.replace(" ", "_")
        # Add a newline to command before sending it to the remote device.
        SendCmd = SendCmd + "\n"

        # Create Filename
        filebits = [CmdName, hostname, mydate + ".txt"]
        filename = '-'.join(filebits)
        
        # Capture output and write to file (extension already in filename, so
        # override the default for the function (.txt), or it'll append twice.)
        fullFileName = GetAbsolutePath(session, save_path, filename)
        
        # Write the output of the command to a file.
        WriteOutput(session, SendCmd, fullFileName, ext="")
        
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
    
    # Clean up before closing session
    EndSession(session)
        
    crt.Dialog.MessageBox("Device Documentation Script Complete", "Script Complete", 64)


if __name__ == "__builtin__":
    Main()