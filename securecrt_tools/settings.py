# ################################################   MODULE INFO    ###################################################
# Author: Jamie Caesar
# Email: jcaesar@presidio.com
#
# This file contains the default values and layouts for the various settings used in these scripts.   The global
# settings are used by all of the scripts to know where to write files and whether to create debug logs, etc.
#
# Some scripts also have local settings that only apply to that one script, and those default values are also saved in
# this file for reference by the scripts.
#
#
#

# ################################################     IMPORTS      ###################################################
import os
import json
import logging

# ################################################     GLOBALS      ###################################################

# Global variables that may be used by other programs

global_settings_filename = 'global_settings.json'

global_defs = {'__comment': "USE FORWARD SLASHES OR DOUBLE-BACKSLASHES IN WINDOWS PATHS! SINGLE BACKSLASHES WILL "
                            "ERROR. See https://github.com/PresidioCode/SecureCRT for settings details",
               '__version': "1.0",
               'debug': False,
               'save path': 'ScriptOutput',
               'date format': '%Y-%m-%d-%H-%M-%S',
               'modify term': True
        }



# ################################################     CLASSES      ###################################################


class SettingsImporter():

    def __init__(self, filename, defaults):
        if isinstance(defaults, dict):
            self.defaults = defaults
        else:
            raise ValueError("Defaults are not in dictionary form.")

        self.settings_filename = filename

        # If the settings file exists, read file and return settings.
        if os.path.isfile(self.settings_filename):
            with open(filename, 'r') as json_file:
                try:
                    self.settings = json.load(json_file)
                except ValueError as err:
                    error_str = "Settings import error.\n\nFor Windows paths you MUST either use forward-slashes " \
                                "(C:/Output) or double-backslashes (C:\\\\Output).\n\n Orignial Error: {0}".format(err)
                    raise ValueError(error_str)

            # Validate settings contains everything it should, or fix it.
            if not self.__valid_settings():
                self.__generate_settings(existing=self.settings)
                self.__write()
            # If valid, make sure settings don't need to be updated.
            else:
                self.__update_settings()

        # If the settings file doesn't exist -- write it.
        else:
            self.__generate_settings()
            self.__write()

    def __repr__(self):
        return str(self.get_settings_dict())

    def __generate_settings(self, existing=None):
        """
        A function to generate a settings JSON file, based on the provided defaults.  If existing settings are passed in,
        those will be written on top of the new defaults.  In the end, only the new fields should be added to the existing
        settings.

        :param existing: (Optional) Existing settings that need to be preserved in the new settings.
        """
        new_settings = dict(self.defaults)

        if existing:
            for key in self.defaults:
                if key in existing:
                    new_settings[key] = existing[key]
                # Extra logic due to change of "save_path" to "save path"
                elif key == "save path" and "save_path" in existing:
                    new_settings[key] = existing['save_path']

        self.settings = new_settings

    def __valid_settings(self):
        """
        Checks the imported settings to make sure all required items are included in the defaults

        :return: Boolean if settings are valid.
        """
        if not isinstance(self.settings, dict):
            return False
        else:
            # Check that each key in the defaults exists in the imported settings.
            for setting in self.defaults.keys():
                if setting not in self.settings.keys():
                    return False
            else:
                return True

    def __update_settings(self):
        """
        If the version of the settings is earlier than the current defaults, update the settings to include the new
        items (and remove any that shouldn't exist anymore).
        """
        if "__version" not in self.settings.keys() or self.settings["__version"] != self.defaults["__version"]:
            self.__generate_settings(existing=self.settings)
            self.__write()

    def __write(self):
        settings_dir = os.path.dirname(self.settings_filename)
        if not os.path.isdir(settings_dir):
            os.mkdir(settings_dir)
        with open(self.settings_filename, 'w') as json_file:
            json.dump(self.settings, json_file, sort_keys=True, indent=4, separators=(',', ': '))

    def get_settings_dict(self):
        return self.settings

    def get_setting(self, key):
        if key in self.settings:
            return self.settings[key]
        else:
            return None
