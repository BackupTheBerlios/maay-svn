"""provides configuration (command line / config file) helpers for Maay"""

__revision__ = '$Id$'

import os

import sys

from logilab.common.configuration import Configuration as BaseConfiguration

import maay

def __get_data_dir():
    """Return the name of the directory where data files are stored,
    depending on the platform and application setup"""
    maay_dir = os.path.abspath(os.path.dirname(maay.__file__))
    if sys.platform == "win32":
        maay_dir = os.path.normpath(os.path.join(maay_dir, '..','..'))
        _update_env_path(maay_dir)
        return  os.path.join(maay_dir,'data')
    else:
        if maay_dir.startswith('/home') or maay_dir.startswith('/Users'):
            # we are in a development directory
            return os.path.join(maay_dir, 'data')
        else:
            # the application has been installed
            base, last = os.path.split(maay_dir)
            while last and last != 'lib': 
                base, last = os.path.split(base)
            return os.path.join(base,'share', 'maay')
    raise AssertionError("Unknown platform setup")

def _update_env_path(maay_dir):
    assert sys.platform == 'win32', 'This method must not be called on non windows platforms'
    path = []
    if os.environ.get('PATH'):
        path.append(os.environ.get('PATH'))
    for directory in (u'antiword', u'pdftohtml', os.path.join(u'mysql', u'bin')):
        path.append(os.path.join(maay_dir, directory))
    os.environ['PATH'] =  u';'.join(path)

        
def get_path_of(datafile):
    """return the path of a data file, depending on the platform
    Handles development paths for testing as well as deployed paths"""
    path = os.path.join(__get_data_dir(), datafile)
    assert os.path.exists(path), "cannot find %s"%path
    return path

def get_config_dirs():
    if sys.platform == "win32":
        return [os.path.normpath(os.path.join(__get_data_dir(), '..'))]
    else:
        return ['/etc/maay', os.path.expanduser('~/.maay'), '.']                            
    

class Configuration(BaseConfiguration):
    options = []
    config_file = None

    def __init__(self):
        BaseConfiguration.__init__(self, options=self.options,
                                   config_file=self.config_file)

    def load(self):
        if self.config_file:
            for directory in get_config_dirs():
                path = os.path.join(directory, self.config_file)
                if os.path.exists(path):
                    self.load_file_configuration(path)
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

