=======================
SecureCRT Tools Modules
=======================

The following custom modules include the majority of the functionality that is used in the single and multi-device scripts.  The classes described below are designed to handle the common actions that scripts would need into a single method to avoid the need to copy and paste chunks of code into multiple scripts, and to make writing scripts faster and easier than when you have to use the low-level SecureCRT API to interact with devices.

It is important to understand the relationship between the classes listed below.

The classes in the "scripts" module and used to represent the execution of the script itself and that script's interactions with the calling application (primarily SecureCRT).  Since a SecureCRT script has the ability to open multiple tabs to different devices and interact with all of them, any attribute or method that is common to the script and not specific to each open session is defined in the script class.  This class tracks a reference to the main session object, which represents the SecureCRT tab that the script was launched from.

The "sessions" classes represent a session to a remote device, which will usually be the SecureCRT tab that the script was initially launched from.  The Script class has the ability to open a new connection in a new tab, and it will return a reference to a separate Session object so that the script can interact with each session independently.   **NOTE:** SecureCRT does **NOT** support multi-threading so the use of multiple sessions are best used in cases where you do not want to close an existing session before performing actions on another device.  One example can be validating login to a remote device after making AAA changes without disconnecting the original session and potentially locking ourselves out.  A rollback of the changes could be performed if the second session is unable to log into the device.

The "settings" classes are simply used to manage importing, exporting and updating entries in the settings.ini file.  The script object keeps a reference to the settings class so that settings can be retrieved or changed.  This class will also attempt to update/re-write the local settings.ini file (while preserving existing settings) should the default_settings.ini contains settings that do not exist in the local settings file.  This may happen when a new script is created and needs settings available in the settings.ini file.

The "utilities" class contains a bunch of helper functions that can be used to simplify certain common tasks.  These funtions are pure Python which means they do not require interactions with scripts, sessions or settings in any way.  For example, some of these functions will convert a string containing an interface name to the short version (Gi0/0) or the long version (GigabitEthernet0/0), while others perform action like sorting in "human" order (device1, device2, device10) instead of alphanumeric (device1, device10, device2).  Functions of this sort should all be saved in this file when they need to be used by multiple scripts.

.. toctree::
   :maxdepth: 2

   tools-scripts
   tools-sessions
   tools-settings
   tools-utilities