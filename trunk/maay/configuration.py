#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

"""provides configuration (command line / config file) helpers for Maay"""

__revision__ = '$Id$'

import os, os.path as osp
import sys

from logilab.common.configuration import Configuration as BaseConfiguration

import maay

def _get_data_dir():
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
    """Updates PATH to explicitly add antiword, mysql, etc.
       default installation paths
    """
    assert sys.platform == 'win32', 'This method must not be called on non windows platforms'
    path = []
    if os.environ.get('PATH'):
        path.append(os.environ.get('PATH'))
    for directory in (u'pdftohtml', os.path.join(u'mysql', u'bin'), ur'c:\antiword'):
        if path and directory not in path[0]:
            path.append(os.path.join(maay_dir, directory))
    os.environ['PATH'] =  os.pathsep.join(path)

## XXX: proposed replacement for the above function (need to be
##      accepted and tested on windows)
## def XXX_update_env_path(maay_dir):
##     assert sys.platform == 'win32', 'This method must not be called on non windows platforms'
##     path = os.environ.get('PATH', '').split(os.pathsep)
##     for otherPath in (u'pdftohtml', os.path.join(u'mysql', u'bin'), ur'c:\antiword'):
##         if otherPath not in path:
##             path.append(os.path.join(maay_dir, otherPath))
##     os.environ['PATH'] = os.pathsep.join(path)


def get_path_of(datafile):
    """return the path of a data file, depending on the platform
    Handles development paths for testing as well as deployed paths"""
    path = os.path.join(_get_data_dir(), datafile)
    assert os.path.exists(path), "cannot find %s"%path
    return path

def _filter_accessible_files(file_list):
    res = []
    for file_obj in file_list:
        if os.access(file_obj, os.R_OK):
            res.append(file_obj)
    return res

class Configuration(BaseConfiguration):
    options = []
    config_file = None

    def __init__(self, name=None, alternative_config_name=None):
        BaseConfiguration.__init__(self, options=self.options,
                                   config_file=self.config_file,
                                   name=name)
        self.config_name = alternative_config_name or 'maay'

    def load(self):
        if self.config_file:
            for directory in self.get_config_dirs():
                path = os.path.join(directory, self.config_file)
                self.load_file_configuration(path)
        # then override with command-line options
        self.load_command_line_configuration()
    

    def get_config_dirs(self):
        if sys.platform == "win32": # XXX: fix Win32 with self.config_dir attr
            return [os.path.normpath(os.path.join(_get_data_dir(), '..'))]
        else:
            #XXX: should '.' really be an acceptable config dir ?
            return _filter_accessible_files([osp.join('/etc/', self.config_name),
                                             os.path.expanduser('~/.' + self.config_name),
                                            '.'])

    def __getattr__(self, attrname):
        """delegate to self.config when accessing attr on
        Configuration objects. (convenience method)
        """
        try:
            return self.__dict__[attrname]
        except KeyError:
            return getattr(self.config, attrname)

