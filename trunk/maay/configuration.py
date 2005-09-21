"""provides configuration (command line / config file) helpers for Maay"""

__revision__ = '$Id$'

import os

import sys

from logilab.common.configuration import Configuration as BaseConfiguration

import maay

def __get_data_dir():
    """Return the name of the directory where data files are stored,
    depending on the platform and application setup"""
    __maay_dir = os.path.abspath(os.path.dirname(maay.__file__))
    if sys.platform == "win32":
        # Assume we are working on an installed version of Maay
        # XXX FIXME this probably does not work with py2exe
        return  os.path.join(__maay_dir, 'data') 
    else:
        if __maay_dir.startswith('/home') or __maay_dir.startswith('/Users'):
            # we are in a development directory
            return os.path.join(__maay_dir, 'data')
        else:
            # the application has been installed
            base, last = os.path.split(__maay_dir)
            while last and last != 'lib': 
                base, last = os.path.split(base)
            return os.path.join(base,'share', 'maay')
    raise AssertionError("Unknown platform setup")
        
def get_path_of(datafile):
    """return the path of a data file, depending on the platform
    Handles development paths for testing as well as deployed paths"""
    path = os.path.join(__get_data_dir(), datafile)
    assert os.path.exists(path), "cannot find %s"%path
    return path

class Configuration(BaseConfiguration):
    options = []
    config_file = None

    def __init__(self):
        BaseConfiguration.__init__(self, options=self.options,
                                   config_file=self.config_file)

    def load(self):
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

