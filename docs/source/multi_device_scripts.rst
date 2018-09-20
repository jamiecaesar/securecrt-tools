=======================
Multiple Device Scripts
=======================

Multiple Device Scripts are scripts that are designed to be executed while NOT attached to a remote device (You will get an error if you try to launch a multi-device script from a connected tab).  The script will prompt for an input CSV containing all of the hosts and other required details (credentials, jumpbox, etc) to be able to connect all of the devices in the list automatically. The logic of the script will be performed on each device, one at a time.

The device list CSV has required columns that must be included.  These are the Hostname, Protocol, Username columns (case sensitive).  If these columns are missing from your CSV file an error will be returned, because these are the minimum pieces of information required to connect to a device.

Additional columns are allowed to be in the CSV file and will be accessible from the scripts, although the data will never be used if a script is not written to look for a particular column.  For example, the "m_document_device" script will use a column called "Command List" to override which list of commands (in the settings.ini file) are used when documenting that particular device.  The same device list can be used in other multi-device scripts, but they will not try to access that column.  

Some standard columns that will be added with default vaules if missings are "Password", "Enable" and "Proxy Session":

* The "Password" field lets you override the password used with that device.  Generally this is left blank because the script will prompt for a password when one isn't defined so that you aren't required to save a password in the file.  This field may still be useful when a particular device has a different password for the same username.  
* The "Enable" column will override the default enable password that the script uses (based on prompting the user). 
* The "Proxy Session" column can override the default SecureCRT session to use as a proxy to reach the target device.  The default SecureCRT session is in the settings.ini file (as well as a flag on whether to use a proxy or not).

Below is a list of multi-device scripts available with this release of SecureCRT Tools.


.. toctree::
   :maxdepth: 1

   m_cdp_to_csv
   m_document_device
   m_find_macs_by_vlans
   m_merged_arp_to_csv
   m_save_output
   m_update_interface_desc

   