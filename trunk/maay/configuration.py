"""provides configuration (command line / config file) helpers for Maay"""

__revision__ = '$Id$'

import os

from logilab.common.configuration import Configuration as BaseConfiguration

class Configuration(BaseConfiguration):
    options = []
    config_file = None

    def __init__(self):
        BaseConfiguration.__init__(self, options=self.options,
                                   config_file=self.config_file)

    def load(self):
        print "CONFIG FILE =", self.config_file
        # first, load config from file
        if self.config_file and os.path.exists(self.config_file):
            self.load_file_configuration(self.config_file)
        # then override with command-line options
        self.load_command_line_configuration()
    

    def __getattr__(self, attrname):
        """deletage to self.config when accessing attr on
        Configuration objects. (convenience method)
        """
        try:
            return self.__dict__[attrname]
        except KeyError:
            return getattr(self.config, attrname)

