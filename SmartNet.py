# $language = "python"
# $interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Michael Ethridge
#
# This script will connect to all SecureCRT sessions in a folder (and
# sub-folders) and and run the basic inventory and version commands needed for
# SmartNet.
#
# The results of each command are written to an individual log file ( one log
# file for each command).
#

###############################  SCRIPT SETTING  ###############################
#
# Settings for this script are saved in the "script_settings.py" file that
# should be located in the same directory as this script.
#

##################################  IMPORTS  ##################################
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

# Import Settings from Settings File or Default settings
try:
    from script_settings import settings
except IOError:
    from script_settings_default import settings

# Imports from common SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import ExpandPath
from ciscolib import GetDateString
from ciscolib import GetAbsolutePath
from ciscolib import WriteOutput

##################################  SCRIPT  ###################################

# Location of SecureCRT Session Directory
my_session_dir = "~/Dropbox/VanDyke/Config/Sessions/"
# Specific sub-folder inside Session folder.  Leave blank to use all Sessions
# site dir must end with / if you use them.
# my_site_dir = "Site1/"
my_site_dir = "Test/"

# Be careful when adding to this list.  If you forget a "," then those two
# commands strings will run together into a single string and sent to the
# device, meaning that neither output will be captures.
#
# The last entry MUST NOT have a comma after it, which might happen if you
# comment out the last line.
COMMANDS = [
    "show inventory",
    "show hardware",
    "show hardware inventory",
    "show version"
]


def GetSessions(Session_Dir, Site_Dir):
    '''
    This function will get all the session names in a starting directory and all
    subdirectories.
    '''
    # Files in Session directories to ignore
    blacklist = ["__FolderData__.ini"]

    # Extention of all Session files in .ini so we'll only look for those
    extension = ".ini"

    # Get list of Sessions
    SessionList = []
    Root_Dir = ExpandPath(Session_Dir) + Site_Dir
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


def Main():
    errorMessages = ""

    # Get Sessions
    sessionsArray = GetSessions(my_session_dir, my_site_dir)

    # Connect to each session and issue a few commands, then disconnect.
    for my_session in sessionsArray:
        try:
            crt.Session.Connect("/S \"" + my_session + "\"")
        except ScriptError:
            error = crt.GetLastErrorMessage()

        # If we successfully connected, we'll do the work we intend to do...
        # otherwise, we'll skip the work and move on to the next session in
        # the list.
        if crt.Session.Connected:

            crt.Sleep(1000)
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
                hostip = crt.Session.RemoteAddress
                filehostip = hostip.replace(".", "_")
                filehostname = hostname.replace("/", "-")
                filehostname = hostname.replace("\\", "-")
                filebits = [filehostname, filehostip, CmdName, mydate + ".txt"]
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

            # Now disconnect from the remote machine...
            crt.Session.Disconnect()
            # Wait for the connection to close
            while crt.Session.Connected == True:
                crt.Sleep(100)
            crt.Sleep(1000)
        else:
            errorMessages = errorMessages + "\n" + "*** Error connecting to " + my_session + ": " + error

    if errorMessages == "":
        crt.Dialog.MessageBox("No Errors were detected.")
    else:
        crt.Dialog.MessageBox("The following errors occurred:\n" + errorMessages)


if __name__ == "__builtin__":
    Main()
