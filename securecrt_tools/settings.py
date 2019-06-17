import ConfigParser
import os


class SettingsImporter:
    """
    A class to handle validating, retrieving and updating settings as needed.
    """
    def __init__(self, settings_file, create=False):
        self.settings_file = settings_file

        # Load Defaults
        default_settings_filename = "default_settings.ini"
        settings_dir = os.path.dirname(__file__)
        self.default_filename = os.path.join(settings_dir, default_settings_filename)
        self.defaults = ConfigParser.RawConfigParser()
        self.defaults.read(self.default_filename)

        # Load custom settings
        self.config = ConfigParser.RawConfigParser()
        if not os.path.isfile(self.settings_file):
            if create:
                settings_dir = os.path.dirname(self.settings_file)
                if not os.path.exists(settings_dir):
                    os.makedirs(settings_dir)
                with open(self.settings_file, 'w') as settings_fp:
                    self.defaults.write(settings_fp)
            else:
                raise IOError("Settings file does not exist: {0}".format(self.settings_file))
        self.config.read(self.settings_file)
        if not self.validate_settings():
            self.correct_settings()
            self.config.read(self.settings_file)

    def validate_settings(self):
        """
        A method to check if the user's settings.ini file contains all of the correct settings.

        :return: A boolean describing if the user's settings file is valid
        :rtype: bool
        """
        # Verify that all of the default sections exist in the user's INI file.  Do this by converting the default and
        # custom section lists to sets, and check that the defaults is a subset of custom.
        if set(self.defaults.sections()).issubset(set(self.config.sections())):
            # All default sections exist.  Now for each default section, make sure the default settings exist in the
            # custom setting using the same method as for sections.
            for section in self.defaults.sections():
                if not set(self.defaults.options(section)).issubset(set(self.config.options(section))):
                    return False
        else:
            return False
        return True

    def correct_settings(self):
        """
        A method to update the user's settings file to match the current correct version while carrying over current
        values to the new file.  Adds anything in defaults that isn't in the user's settings to the settings.ini file.
        This does not remove any additions that may have been added to the user's configuration file.
        """
        # Create a new collection of settings, based on the defaults
        new_settings = ConfigParser.RawConfigParser()
        new_settings.read(self.default_filename)

        # Loop through all the current settings and add values to the new settings as needed.
        for section in self.config.sections():
            # Check if section exists in new settings.  If not, create it.
            if section not in new_settings.sections():
                new_settings.add_section(section)

            # Check each existing option in the section and write it to the new settings.
            for option in self.config.options(section):
                value = self.config.get(section, option)
                new_settings.set(section, option, value)

        # Write our new collection of settings to the user's custom settings.ini file.
        with open(self.settings_file, 'w') as my_new_settings:
            new_settings.write(my_new_settings)

    def get(self, section, setting):
        """
        A wrapper function to simplify the retrieval of an individual setting.

        :param section: The section of the settings file where the setting can be found.
        :type section: str
        :param setting: The name of the setting we want to retrieve
        :type setting: str

        :return: The value of the setting requested
        :rtype: str
        """
        return self.config.get(section, setting)

    def update(self, section, setting, value):
        """
        A wrapper function to update a setting

        :param section: The section of the settings file where the setting can be found.
        :type section: str
        :param setting: The name of the setting we want to retrieve
        :type setting: str
        :param value: The value to store for this setting
        :type value: str
        """
        self.config.set(section, setting, value)
        with open(self.settings_file, 'w') as settings_updates:
            self.config.write(settings_updates)

    def getboolean(self, section, setting):
        """
        A wrapper function to simplify the retrieval of an individual setting as a boolean value.

        :param section: The section of the settings file where the setting can be found.
        :type section: str
        :param setting: The name of the setting we want to retrieve
        :type setting: str

        :return: The value of the setting requested as a boolean
        :rtype: bool
        """
        return self.config.getboolean(section, setting)

    def getint(self, section, setting):
        """
        A wrapper function to simplify the retrieval of an individual setting as an integer.

        :param section: The section of the settings file where the setting can be found.
        :type section: str
        :param setting: The name of the setting we want to retrieve
        :type setting: str

        :return: The value of the setting requested as an integer
        :rtype: int
        """
        return self.config.getint(section, setting)

    def getlist(self, section, setting):
        """
        A wrapper function to simplify the retrieval of an individual setting as a list.  Requires the setting to be
        a comma separated list, with no quotations.

        :param section: The section of the settings file where the setting can be found.
        :type section: str
        :param setting: The name of the setting we want to retrieve
        :type setting: str

        :return: The value of the setting requested as a list.
        :rtype: int
        """
        # Get the raw string from the settings file.
        raw_setting = self.config.get(section, setting)
        # Split the raw string on the comma, and save each item as an entry into the list, while removing
        return filter(None, map(lambda x: x.strip(), raw_setting.split(',')))
