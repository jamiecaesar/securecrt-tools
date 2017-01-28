# $language = "python"
# $interface = "1.0"

################################  MODULE  INFO  ################################
# Author: Jamie Caesar
# Twitter: @j_cae
#
#    !!!! NOTE:  THIS IS NOT A SCRIPT THAT CAN BE RUN IN SECURECRT. !!!!
#
# This is a Python module that contains the settings that are used by the 
# other scripts. These are kept in a separate file so that when script updates
# are pushed, they can be merged into everyone's repository without overwriting
# the settings that each individual person uses.
#
#

# Create data structure (dictionary) that holds our settings.
settings = {}
###############################  SCRIPT SETTING  ###############################
#
#
#------------------------------- Global Settings -------------------------------
#
#
#### WHERE TO SAVE FILES:
# Enter the path to the directory where the script output should be stored.
# This can either be a relative path (which will start in the user's home
#   directory) or an absolute path (i.e. C:\Output or /Users/Jamie/Output).
settings['savepath'] = 'ScriptOutput'
# The script will use the correct variable based on which OS is running.
#
#
#### FILENAME FORMAT
# Choose the format of the date string added to filenames created by this script.
# Example = '%Y-%m-%d-%H-%M-%S'
# See the bottom of https://docs.python.org/2/library/datetime.html for all 
# available directives that can be used.
settings['date_format'] = '%Y-%m-%d-%H-%M-%S'
#
#
#------------------------------- Script Specific ------------------------------
#
#
#### DELETE TEMP FILES
## Used by: NextHopSummary, InterfaceStats, SaveCDPtoCSV
# For scripts that save the output into a file so that the output can be worked
# with easier (large outputs going directly into variables can bog down and 
# crash).  If you want to keep the raw output file, set this to False, otherwise
# it will be deleted, leaving only the intended script output
settings['delete_temp'] = True
#
#### SHOW ALL VLANs
## Used by: UsedVlANS
# If this value is true, then the output will list all VLANs, even those with 0 
# ports allocated.   If False, it will only list VLANs with at least 1 port
# allocated.
settings['show_all_VLANs'] = False
###############################  END OF SETTINGS ###############################


#######################  DISPLAY ERROR IF RAN DIRECTLY  #######################

def Main():
    error_str = "This is not a SecureCRT Script,\n" \
                "But a python module that holds\n" \
                "functions for other scripts to use.\n\n" \

    crt.Dialog.MessageBox(error_str, "NOT A SCRIPT", ICON_STOP)

if __name__ == "__builtin__":
    Main()

