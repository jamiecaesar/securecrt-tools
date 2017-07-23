# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: XXXXXXXX
# Email: XXXXXXX@presidio.com
# 
# ****WRITE A DESCRIPTION OF WHAT THIS SCRIPT SHOULD DO HERE*****
#

# ##############################  SCRIPT SETTING  ###############################
#
# Global settings that affect all scripts (output directory, date format, etc) is stored in the "global_settings.json"
# file in the "settings" directory.
#
# If any local settings are used for this script, they will be stored in the same settings folder, with the same name
# as the script that uses them, except ending with ".json".
#
# All settings can be manually modified with the same syntax as Python lists and dictionaries.   Be aware of required
# commas between items, or else options are likely to get run together and neither will work.
#
# **IMPORTANT**  All paths saved in .json files must contain either forward slashes (/home/jcaesar) or
# DOUBLE back-slashes (C:\\Users\\Jamie).   Single backslashes will be considered part of a control character and will
# cause an error on loading.
#


# #################################  IMPORTS  ##################################
# Import OS and Sys module to be able to perform required operations for adding the script directory to the python
# path (for loading modules), and manipulating paths for saving files.
import os
import sys

# Add the script directory to the python path (if not there) so we can import custom modules.
script_dir = os.path.dirname(crt.ScriptFullName)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Imports from custom SecureCRT modules
from imports.cisco_securecrt import start_session
from imports.cisco_securecrt import end_session


# #################################  SCRIPT  ###################################


def main():
        """
        Put a description of what the script will do here
        """

        # Run session start commands and save session information into a dictionary
        session = start_session(crt, script_dir)

        # Make sure we completed session start.  If not, we'll receive None from start_session.
        if session:
            #
            # PUT YOUR CODE HERE
            #

            # Clean up before closing session
            end_session(session)

if __name__ == "__builtin__":
    main()