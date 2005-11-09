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
import re
import sha
import platform
import time

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

def _filter_files_with(file_list, access_criterium):
    return [file_obj for file_obj in file_list
            if os.access(file_obj, access_criterium)]

class Configuration(BaseConfiguration):
    options = [
        ('config-name',
         {'type' : "string", 'metavar' : "<config-name>", 'short' : "C",
         'help' : "allow to specify a config directory name",
          'default' : "maay",
        })]
    config_file = None

    def __init__(self, name=None):
        BaseConfiguration.__init__(self, options=self.options,
                                   config_file=self.config_file,
                                   name=name)
        self.load_command_line_configuration()
        self.config_name = self['config-name']

    def load(self):
        if self.config_file:
            for directory in self.get_config_dirs():
                path = os.path.join(directory, self.config_file)
                self.load_file_configuration(path)
        # then override with command-line options
        self.load_command_line_configuration()
    

    def get_config_dirs(self):
        if sys.platform == "win32": # XXX: fix Win32 with self.config_name attr
            return [os.path.normpath(os.path.join(_get_data_dir(), '..'))]
        else:
            #XXX: should '.' really be an acceptable config dir ?
            return _filter_files_with([osp.join('/etc/', self.config_name),
                                       os.path.expanduser('~/.' + self.config_name),
                                       '.'],
                                      os.R_OK)

    def get_writable_config_dirs(self):
        return _filter_files_with(self.get_config_dirs(), os.W_OK)

    def __getattr__(self, attrname):
        """delegate to self.config when accessing attr on
        Configuration objects. (convenience method)
        """
        try:
            return self.__dict__[attrname]
        except KeyError:
            return getattr(self.config, attrname)

################ Web server, rpc server stuff

class WebappConfiguration(Configuration):
    options = Configuration.options + [
        ('db-name',
         {'type' : "string", 'metavar' : "<dbname>", 'short' : "d",
          'help' : "name of the Maay database",
          'default' : "maay",
          }),
        ('db-host',
         {'type' : "string", 'metavar' : "<dbhost>", 'short' : "H",
          'help' : "which server hosts the database",
          'default' : "localhost",
          }),
        ('user',
         {'type': 'string',
          'metavar': '<userid>', 'short': 'u',
          'help': 'login of anonymous user to use to connect to the database',
          'default' : "maay",
          }),
        ('password',
         {'type': 'string',
          'metavar': '<password>', 'short' : "p",
          'help': 'password of anonymous user to use to connect to the database',
          'default' : "maay",
          }),
        ('registration-host',
         {'type' : "string", 'metavar' : "<registration_host>", 
          'help' : "Host name or IP address of the registration server",
          'default' : "localhost",
          }),
        ('registration-port',
         {'type' : "int", 'metavar' : "<registration_port>", 
          'help' : "Internet port on which the registration server is listening",
          'default' : 2345,
          }),
        ('webserver-port',
         {'type' : "int", 'metavar' : "<webserver_port>", 
          'help' : "Internet port on which the web interface is listening",
          'default' : 7777,
          }),
        ('rpcserver-port',
         {'type' : "int", 'metavar' : "<rpcserver_port>", 
          'help' : "Internet port on which the xmlrpc server is listening",
          'default' : 6789,
          }),
        ('bandwidth',
         {'type' : "int", 'metavar' : "<bandwidth>", 
          'help' : "Internet port on which the xmlrpc server is listening",
          'default' : 10,
          }),
        ('nodeid-file',
         {'type' : "string", 'metavar' : "<node_id_file>",
          'help' : "Maay will store the generated node id in this file",
          'default' : "node_id",
          }),
        ]

    config_file = 'webapp.ini'

    def __init__(self):
        Configuration.__init__(self, name="Server")
        self.node_id = None

    def get_node_id(self):
        if not self.node_id:
            self.node_id = self._read_node_id()
        return self.node_id

    def _read_node_id(self):
        for directory in self.get_writable_config_dirs():
            try:
                filename = os.path.join(directory, self.nodeid_file)
                f = open(filename,'r')
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    node_id = line.strip()
                    assert re.match('^[0-9a-fA-F]{40}$', node_id)
                    f.close()
                    return node_id
            except IOError:
                continue
        self._write_node_id()
        return self._read_node_id()

    def _generate_node_id(self):
        hasher = sha.sha()
        hasher.update(''.join(platform.uname()))
        hasher.update('%s' % id(self))
        hasher.update('%s' % time.time())
        return hasher.hexdigest()

    def _write_node_id(self):
        node_id = self._generate_node_id()
        for directory in self.get_writable_config_dirs():
            try:
                filename = os.path.join(directory, self.nodeid_file)
                f = open(filename, 'w')
                lines = ['# This file contains the Node Identifier for your computer\n',
                         '# Do not edit it or erase it, or this will corrupt the database\n',
                         '# of your Maay instance.\n',
                         '# This id was generated on %s\n' % time.asctime(),
                         '%s\n' % node_id
                         ]
                f.writelines(lines)
                f.close()
                return
            except IOError:
                continue
        raise ValueError('Unable to find a writable directory to store the node id')

################ Image stuff 

class NoThumbnailsDir(Exception):
    """Represents impossibility to access or create RW the
       maay thumbnails dir repository"""
    pass

class ImageConfiguration(Configuration):
    options = Configuration.options + [
        ('thumbnails-dir',
         {'type' : "string", 'metavar' : "--thumbnailsdir", 'short' : "-thumbs",
          'help' : "Thumbnail files repository",
          'default' : '.maay_thumbnails'},)]
    config_file = 'image.ini'

    def __init__(self):
        Configuration.__init__(self, name="Image")

    def get_thumbnails_dir(self):
        """Returns the complete path to Maay thumnails directory
           XXX: It will try to create the dir if absent"""
        path = osp.join(osp.expanduser('~'),
                        self.get('thumbnails-dir'))
        if not os.access(path, os.W_OK):
            try:
                os.makedirs(path, stat.S_IRWXU)
            except Exception, e:
                raise NoThumbnailsDir("Impossible to access or create %s. "
                                      "Cause : %e" % (path, e))
        if os.access(path, os.W_OK): # yes, I'm paranoId
            return path
        else:
            raise NoThumbnailsDir("Access to %s is impossible." % path)



################ Indexer stuff 

class IndexerConfiguration(Configuration):
    options = Configuration.options + [
        ('host',
         {'type' : "string", 'metavar' : "<host>", 'short' : "H",
          'help' : "where Maay node can be found",
          'default' : "localhost",
          }),

        ('port',
         {'type' : "int", 'metavar' : "<int>", 'short' : "P",
          'help' : "which port to use",
          'default' : 6789,
        }),

        ('user',
         {'type': 'string',
          'metavar': '<userid>', 'short': 'u',
          'help': 'identifier to use to connect to the database',
          'default' : "maay",
          }),

        ('password',
         {'type': 'string',
          'metavar': '<password>', 'short' : "p",
          'help': 'password to use to connect to the database',
          'default' : "maay",
          }),

        ('private-index-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 'i',
          'help': 'index this directory with the private indexer',
          'default' : []
          }),
         
        ('private-skip-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 's',
          'help': 'the private indexer will skip this directory',
          'default' : []
          }),
        ('public-index-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 'I',
          'help': 'index this directory with the public indexer',
          'default' : []
          }),
         
        ('public-skip-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 'S',
          'help': 'the public indexer will skip this directory',
          'default' : []
          }),

        ('verbose',
         {'type': 'yn',
          'metavar': '<y or n>', 'short': 'v',
          'help': 'enable verbose mode',
          "default": False,
          }),
        ('purge',
         {'type' : 'yn',
          'help' : 'purge the set of indexed documents and returns immediately',
          'metavar' : '<y or n>',
          'default' : False,
          }),
        ]

    config_file = 'indexer.ini'

    def __init__(self):
        Configuration.__init__(self, name="Indexer")
