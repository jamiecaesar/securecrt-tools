Introduction
==================
This repository contains a collection of SecureCRT scripts that automate various tasks, primarily around interacting with Cisco routers and switches.

These scripts should work on any version of SecureCRT that supports python.  If you find that a script won't work on your machine, please post an issue to let us know!

Important Note
==============
The settings files for these scripts have been changed from using JSON files to the Python built-in ConfigParse module.  In addition instead of each script uses indivdiual settings having its own JSON file, now that settings are saved in the common "settings.ini" file under a separate heading for that script.  **There is no code to migrate your settings from the old JSON format to the INI format, so please check your settings and remove the old JSON files**

In addition to the new format for the settings, the newer version of these scripts now have support for initiating connections via Telnet and SSH to remote devices, as well as connecting via a jump/bastion host.  In addition there are methods for pushing configuration changes to devices that were not available previously.

If you are looking for previous versions of the scripts, they can be found in the branches below:
* Please see the `Pre-2017` branch if you need to access the original versions (1.0) that were all function based.
* Please see the `2017` branch if you want the original class-based scripts use the JSON based settings files. (2.0)

Running The Scripts
===================
There are 2 types of scripts in this repository:
1) Scripts that interact with a single device, AFTER you have logged in manually (starts with 's\_'), and
2) Scripts that interat with multiple devices, where the script performs the login action (starts with 'm\_')

The run any of these scripts, you need to download the entire repo to your computer.  You can either clone the repository or download an archive to extact on your machine.

Single Device Scripts
*********************
To run SINGLE device scripts, do the following:

1) **AFTER** connecting to a device in SecureCRT, go to the *Scripts* menu and select "Run"

2) Choose the script you want to run (that starts with 's\_')

3) The script looks for your `settings.ini` file. If this file doesn't exist (and it won't the first time you run one of these scripts) the script will create the file.

4) If the script produces an output, it will be saved in the directory specified in the `settings/settings.ini` file.  If this diretory does not exist, you will be prompted to create it.  You can modify this path to choose where the scripts save outputs.

The output files are automatically named based on the hostname of the device connected to.   This name is taken from the prompt of the device, so these scripts will work whether you are directly connected, or connected via a jumpbox or other intermediate device.

Multiple Device Scripts
***********************
1) While **NOT** connected to a device, go to the *Scripts* menu and select "Run"

2) The script will prompt you to select a CSV file that contains all the required information for the devices the script should connect to.  You will be prompted for credentials, if required.

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

Some scripts have local settings files that only apply to that script.  If such a setting is needed, the setting will be saved under a heading named for the script in the `settings.ini` file.  Details about the settings should be in the docstring for that particular script file.

Documentation
=============

The detailed documentation for this project can be found at `http://jamiecaesar.github.io/securecrt-tools/ <http://jamiecaesar.github.io/securecrt-tools/>`_.
