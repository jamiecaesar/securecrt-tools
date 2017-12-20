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

Documentation
=============

The detailed documentation for this project can be found at `http://jamiecaesar.github.io/securecrt-tools/ <http://jamiecaesar.github.io/securecrt-tools/>`_.
