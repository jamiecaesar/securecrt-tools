# $language = "python"
# $interface = "1.0"

# ###############################  SCRIPT INFO  ################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
# 
# This script will grab the running configuration of a Cisco IOS or NX-OS device and save it into a file.
#

# ##############################  SCRIPT SETTING  ###############################
#
# Settings for this script are saved in the "script_settings.json" file that should be located in the same directory as
# this script.
#


# #################################  IMPORTS  ##################################
# Import OS and Sys module to be able to perform required operations for adding the script directory to the python
# path (for loading modules), and manipulating paths for saving files.

import sys

# #################################  SCRIPT  ###################################

def main():
    crt.Dialog.MessageBox(sys.version)

if __name__ == "__builtin__":
    main()