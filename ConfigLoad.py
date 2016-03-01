#$language = "python"
#$interface = "1.0"

################################  SCRIPT INFO  ################################
# Author: Michael Ethridge
#
# ConfigLoad.py
#
# Description:
#   Load configuration commands from a file to a Cisco device
#
#   Each line of the input file is copied to an output file in the same directory
#   with "Config_Load" and the date time stamp added to the file name
#
#   If a line produces an error, it is copied with '*** Invalid Command : '
#   prepended to the line.
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

# Import Settings from Settings File
from script_settings import settings

# Imports from Cisco SecureCRT library
from ciscolib import StartSession
from ciscolib import EndSession
from ciscolib import GetDateString
from ciscolib import DEFBUTTON2
from ciscolib import ICON_QUESTION
from ciscolib import BUTTON_YESNO
from ciscolib import IDYES

##################################  SCRIPT  ###################################


def get_configfile():
    # Initialize variable for path to config file to be loaded
    l_configfile = ""

    # Prompt for config file to be loaded
    l_configfile = crt.Dialog.FileOpenDialog(
        "Please select the config file to be loaded.",
        "Open",
        l_configfile,
        "Text Files (*.txt)|*.txt|CFG Files (*.cfg)|*.cfg|All Files (*.*)|*.*||")

    # Determine if we got a config file and return the file path or False
    if l_configfile == "":
        return False
    else:
        return l_configfile


def main():
    # Get configfile to load
    configfile = get_configfile()

    # See if we got our input file
    if configfile != "":
        #Do we continue on errors or not?
        result = crt.Dialog.MessageBox("Stop on Errors?", "Error", ICON_QUESTION | BUTTON_YESNO | DEFBUTTON2)
        if result == IDYES:
            error_stop = True
        else:
            error_stop = False

        # Run session start commands and save session information into a dictionary
        session = StartSession(crt)

        # Get CRT Tab for sending commands
        tab = session['tab']

        # Define the line endings we are going to look for while entering commands
        endings = ["\r\n", ")#"]

        # Get the current date in the format supplied in date_format
        my_date = GetDateString(settings['date_format'])

        # Define variable to be used to identify if we are sending banner config lines and end mark
        banner_lines = False
        end_of_banner = ""

        # Define my_line_count variable to tell where we found an error, if we do.
        my_line_count = 0

        # Break out the input file path and name minus the extension so we can create output filename
        c_filename, c_extension = os.path.splitext(configfile)

        # Create Filename
        file_bits = [c_filename, "Config_Load", my_date + c_extension]
        output_file = '-'.join(file_bits)

        # Open the output file for writing
        out_file = open(output_file, 'w')

        # Write header to output file
        out_file.write('Output of all Configuration Commands\r\n')
        out_file.write('Error Lines will start with *** Invalid Command :\r\n')
        out_file.write('\r\n========\r\n')

        # Enter configuration mode
        tab.Send("config term\n")

        # Loop through each line of the input config file.
        with open(configfile, "rU") as InputFile:
            for line in InputFile:
                try:
                    # Increment line count
                    my_line_count += 1
                    # Strip line endings so as not to get double spacing
                    line = line.strip()
                    # Send line to device
                    tab.Send(line + "\n")
                    # Check to see if it was a banner line as we won't get the prompt back
                    if "banner" in line:
                        banner_lines = True
                        # Determine what the end of banner character is going to be
                        end_of_banner = line[-1]
                    # If we're still processing banner lines continue
                    elif banner_lines:
                        # Check if end of Banner
                        if line == end_of_banner:
                            banner_lines = False
                        # Wait for echo of banner line
                        tab.WaitForString(line.strip())
                    else:
                        # Wait for echo of config command
                        tab.WaitForString(line.strip())

                    # Loop to capture every line of output.  If we get CR/LF (first entry
                    # in our "endings" list), then write that line to the file.  If we get
                    # our prompt back (which won't have CR/LF), break the loop b/c we found the
                    # end of the output.
                    while True:
                        next_line = tab.ReadString(endings)
                        # If the match was the 1st index in the endings list -> \r\n
                        if tab.MatchIndex == 1:
                            # Strip newlines from front and back of line.
                            next_line = next_line.strip('\r\n')
                            # If there is something left, check for Invalid command.
                            if "% Invalid" in next_line:
                                # Strip line endings from line.  Also re-encode line as ASCII
                                # and ignore the character if it can't be done (rare error on
                                # Nexus)
                                out_file.write(
                                    '*** Invalid Command : ' + line.strip('\r\n').encode('ascii', 'ignore') + '\r\n'
                                )
                                # If we're stopping on errors, raise an exception so we'll stop on next iteration
                                if error_stop:
                                    raise NameError('InvalidCommand')
                                break
                            elif banner_lines:
                                # write out banner lines as a special case
                                out_file.write(line.strip('\r\n').encode('ascii', 'ignore') + '\r\n')
                                break
                        else:
                            # We got our prompt (MatchIndex is 2), so break the loop
                            out_file.write(line.strip('\r\n').encode('ascii', 'ignore') + '\r\n')
                            break
                # If we've raised an exception for an Invalid command and are supposed to stop
                # present a dialog box with a message indicating which line had the invalid command.
                except NameError:
                    crt.Dialog.MessageBox("Invalid Command Found\n On line: " + str(my_line_count), "Error", 16)
                    break

        # End configuration mode
        tab.Send("end\n")

        # Close input and output files
        out_file.close()
        InputFile.close()
        # Clean up before closing session
        EndSession(session)

        # Show dialog with completion message
        crt.Dialog.MessageBox("Config Load Complete", "Script Complete", 64)

    else:
        crt.Dialog.MessageBox("No Configfile Provided", "Error", 16)


if __name__ == "__builtin__":
    main()
