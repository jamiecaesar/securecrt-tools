Introduction
==================
This repository contains a collection of SecureCRT scripts that automate various tasks, primarily around interacting with Cisco routers and switches.

These scripts should work on any version of SecureCRT that supports python.  If you find that a script won't work on your machine, please post an issue to let us know!

Important Note For Users of Older Versions
==========================================
The settings files for these scripts have been changed from using JSON files to the Python built-in ConfigParse module.  In addition instead of each script uses indivdiual settings having its own JSON file, now that settings are saved in the common "settings.ini" file under a separate heading for that script.  **There is no code to migrate your settings from the old JSON format to the INI format, so please check your settings and remove the old JSON files**

In addition to the new format for the settings, the newer version of these scripts now have support for initiating connections via Telnet and SSH to remote devices, as well as connecting via a jump/bastion host.  In addition there are methods for pushing configuration changes to devices that were not available previously.

If you are looking for previous versions of the scripts, they can be found in the branches below:
* Please see the `Pre-2017` branch if you need to access the original versions (1.0) that were all function based.
* Please see the `2017` branch if you want the original class-based scripts use the JSON based settings files. (2.0)

What These Scripts Do
=====================
While the documentation has a detailed list of every script in this collection and the specifics on how they work, below is a summarized list of the kinds of things these scripts will do.

* Save command outputs from devices into files that are automatically named with the hostname of the device (from the prompt) and a time/date stamp.  There are some different versions depending on if you want a single output or multiple outputs and from one or multiple devices.
* Capture device inventory data (code version, model number, serial number, mfg. date, etc.) for a list of devices provided to the script in CSV format.
* Write the detailed CDP neighbor information into a spreadsheet (CSV format) for easier viewing and re-use of the data.
* Creation of SecureCRT sessions from the CDP information of a device, to quickly build your collection of sessions in SecureCRT's session manager.
* Summarize the route table of a device to see a list of all next-hops found in the route table and how many routes from which routing protocols are sending routes to each next-hop.  This script is useful either as a validate tool after routing changes (see a summary of route behavior before and after the change), or to help with discovery of new devices (There are 4000 routes in the table, but are there 3 or 30 exits that packets can take?)
* Write the ARP table for a device into a spreadsheet (CSV) file, either for manual lookups or to be leveraged by other scripts (see below).  There is also version that will build a single large ARP table from multiple devices (For when HSRP priorities are split across 2 cores, or multiple VRFs route different VLANs upstream).
* Create a spreadsheet that maps out every device on the switch, including interface description, MAC Address, MAC Vendor and IP address.  This script uses the ARP table created above as input if you want MAC to IP mappings shown in the output.
* Capture the interface stats from all interfaces on a device into a spreadsheet to more quickly see which ports have errors, high rates of traffic, etc.
* Search devices for specific existing IP helper/DHCP relay addresses and add new relays (optionally remove old) on any interface where the current relays are found.  There are versions of this script for working with a single device or a list of devices.

These various scripts are included in the repository so that someone can quickly download them and get started, but majority of the work has been put into building the `securecrt_tools` module which is designed to handle all of the low-level interactions with SecureCRT and make it as easy as possible to write new scripts.  This module handles discovering the remote device OS, its prompt and hostname, and the interactions with the device.  For example a single method call can send a command, collect the output and write it to a file named after the device.  This way a script should be able to gather the output needed in a few lines of code and anything beyond that is the processing required to parse that output (TextFSM makes this much easier) and take the appropriate follow up steps.  All of this is discussed in more detail in the "Writing Your Own Scripts" sectin of the documentation.

Using a Jumpbox/Bastion Host
============================
In some cases you can only access a remote device by proxying through a jump box/bastion host.  Fortunately, SecureCRT already has a method of handling this and so I don't have to build the code directly into the securecrt_tools module to do it.  The steps for proxying a connection through another device are:

1) Create an SSH2 session to connect to the jump box.  Make sure you can use this session to connect to the jump box directly.

2) Create a session to connect to the remote device by IP or name (that the jump box can resolve).

3) While editing the remote device session, go to the SSH2/SSH1/Telnet section and look for the `Firewall` drop down.

4) Choose `Select Session` and select the session for the jump box.

5) When you launch the remote device session, you'll first be prompted for the jump box credentials (unless you've saved them) and then you'll be prompted for the remote device credentials.  You should now be connected to the remote device by proxying through the jump box.

For more information, watch the video on VanDyke Software's YouTube channel at `https://youtu.be/XHOVTuv-LKY <https://youtu.be/XHOVTuv-LKY>`_.

Running The Scripts
===================
There are 2 types of scripts in this repository:

1) Scripts that interact with a single device, AFTER you have logged in manually (starts with 's\_'), and

2) Scripts that interat with multiple devices, where the script performs the login action (starts with 'm\_')

A list of all the single- and multi-device scripts and descriptions on what they do can be found in the documentation below.

The run any of these scripts, you need to download the entire repo to your computer.  You can either clone the repository or download an archive to extact on your machine.

Single Device Scripts
*********************
To run SINGLE device scripts, do the following:

1) **AFTER** connecting and logging into a device with SecureCRT, go to the *Scripts* menu and select "Run"

2) Choose the script you want to run (that starts with 's\_')

3) The script looks for your `settings.ini` file. If this file doesn't exist (and it won't the first time you run one of these scripts) the script will create the file.

4) If the script produces an output, it will be saved in the directory specified in the `settings/settings.ini` file.  If this diretory does not exist, you will be prompted to create it.  You can modify this path in the `settings.ini` file to change where the scripts save the output they produce.

The output files are automatically named based on the hostname of the device connected to.   This name is taken from the prompt of the device, so these scripts will work whether you are directly connected, or connected via a jumpbox or other intermediate device.

Multiple Device Scripts
***********************
1) While **NOT** connected to a device, go to the *Scripts* menu and select "Run"

2) The script will prompt you to select a CSV file that contains all the required information for the devices the script should connect to.  You will be prompted for credentials, if required.  **A sample device file can be found at `templates/sample_device_list.csv`**

3) The script will connect to each device and execute the script logic.  The script will process one device at a time in the same tab.  While this it the case because SecureCRT does not support multi-threading within scripts, you can manually multi-thread by breaking your devices file into multiple files and lauching the same script in multiple tabs with differnet device files.

Settings
========
All settings files are stored in the `settings/settings.ini` file from the root of the scripts directory.

Global Settings
***************

Global settings that are used by all scripts are under the `Global` heading in the `settings.ini` file.  The following options are available in the global settings file:

* '**output_dir**': This is the path where you want the output from scripts to be saved.  *NOTE* For Windows systems, either use forward slashes (/) or double backslash (\\) to represent a single backslash.  If a single backslash is used, Python may interpret it as an escape character.
* '**date_format**': Default is '%Y-%m-%d-%H-%M-%S'.  This string specifies how the date stamp in output filenames is formatted.
  - %Y - 4-digit Year
  - %m - numeric month
  - %d - day of the month
  - %H - Hours
  - %M - Minutes
  - %S - Seconds
* '**modify_term**': True or False.  When True, the script will attempt to modify the terminal length and width to 0 so that output flows continuously.  When the output is complete the script will return the length and width to their original values.   If False, it will not change the values, but instead auto-advance when a "More" prompt is encountered.
* '**debug_mode**': True or False.  If True, a log file will be written that contains debug messages from the script execution.  This can be helpful for troubleshooting scripts that are failing.  The debug files will be saved in a `debugs` directory under your configured output directory.
* '**use_proxy**': True or False.  If True, scripts that initiate connections (multi-device scripts) will use the `proxy_session` option below to specify which SecureCRT Session to use as a SOCKS proxy.  When enabled, this option uses the `Firewall` setting in the SecureCRT sessions settings to specify the device to proxy the connection through.
* '**proxy_session**': The name of the SecureCRT session that should be used to proxy connections.  This **MUST** be a session that uses SSH2.  Use the forward slash (/) to specify folders in the path to the session, i.e. `proxy_session = Site 1/Core/S1_Core1`.

Script-Specific Settings
************************

Some scripts have settings that are used to change certain behaviors while running.  If such a settings are used, the setting will be saved under a heading named for the script in the `settings.ini` file.  Details about the settings used by a script are described in the documentation for that script, or in the docstring in the script file itself.

Contributing
============
While I've tried to create an assortment of scripts that would be useful to most network professionals, I would love for people to contribute to this repository by adding script and making improvements via pull request. These improvements can include bug fixes or support for additional devices beyond the few Cisco OSes I have access to test against.  The majority of these scripts were created to do things that I've found useful over time, but I'm sure there are plenty more great ideas for scripts that I haven't thought of. 

If you have a need for a script but do not feel confident that you can write one yourself, please post the idea in the issues log and perhaps someone will find the time to write it. Ultimately, if you have the interest, the best way to learn both Python and how to write your own scripts using these tools is by coming up with something you want to build and just keep working at it.  Blank script templates (in the `templates` folder) are provided to help with getting started quickly and all of the existing scripts can be used as examples or modified to suit your needs.  Since there are currently very few contributors to this repository the fastest way to get a new script to do what you need is to try to write it yourself and reach out for feedback and help. I can't guarantee that anyone will have the time to build a suggested script if suggested, but I'd still love to have those ideas posted even if it doesn't meet your timeline.

To help support involvement from others in the community, I've tried to write comprehensive documentation about both the high-level design/logic of the modules and scripts, as well as detailed documentation about all of the functions/methods in the modules. This include docstrings and comments within the code to make it as easy as possible for people new to this repository to understand what it is doing and to understand the existing capabilities thta can be used to save time writing new scripts. Please reach out with any feedback you have on the documentation so it can be continuously improved, even for simple typos and grammar errors that you find (or better yet, create a pull request to fix the file as practice using git and github!)
