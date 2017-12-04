import ConfigParser
import os


class InvalidSettingsError(Exception):
    """
    An exception that is raised when the settings file is invalid or corrupt
    """
    pass


class SettingsImporter:
    """
    A class to handle validating, retrieving and updating settings as needed.
    """
    def __init__(self, settings_file, create=False):
        self.settings_file = settings_file

        # Load Defaults
        default_settings_filename = "default_settings.ini"
        settings_dir = os.path.dirname(__file__)
        default_filename = os.path.join(settings_dir, default_settings_filename)
        self.defaults = ConfigParser.RawConfigParser()
        self.defaults.read(default_filename)

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
                raise IOError("Settings file does not exist: {}".format(self.settings_file))
        self.config.read(self.settings_file)
        if not self.validate_settings():
            self.correct_settings()

    def validate_settings(self):
        """
        A method to check if the user's settings.ini file contains all of the correct settings.

        :return: A boolean describing if the user's settings file is valid
        :rtype: bool
        """
        default_version = self.defaults.getint("Version", "file_version")

        try:
            version = self.config.getint("Version", "file_version")
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            raise InvalidSettingsError("Settings file does not contain Version information.")

        if version == default_version:
            if set(self.defaults.sections()) == set(self.config.sections()):
                for section in self.defaults.sections():
                    if not set(self.defaults.options(section)) == set(self.config.options(section)):
                        return False
            else:
                return False
        else:
            return False
        return True

    def correct_settings(self):
        """
        A method to update the user's settings file to match the current correct version while carrying over current
        values to the new file.
        """
        self.config.set("Version", "file_version", self.defaults.get("Version", "file_version"))
        for section in self.defaults.sections():
            if section not in self.config.sections():
                self.config.add_section(section)
            for option in self.defaults.options(section):
                try:
                    self.config.get(section, option)
                except ConfigParser.NoOptionError:
                    self.config.set(section, option, self.defaults.get(section, option))
        with open(self.settings_file, 'w') as settings_updates:
            self.config.write(settings_updates)

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

    def getboolean(self, section, setting):
        """
        A wrapper function to simplify the retrieval of an individual setting that is a boolean value.

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
        return map(lambda x: x.strip(), raw_setting.split(','))
