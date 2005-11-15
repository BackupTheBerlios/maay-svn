#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""small unit tests for Configuration class"""

import unittest
import sys
import os
import os.path as osp
import re

from maay import configuration
from maay.configuration import NodeConfiguration, ImageConfiguration

class NodeConfigTC(unittest.TestCase):

    def testFromCommandLine(self):
        """For this test to not fail, the configuration file must
           define the database as being 'maay'
        """
        data = [('maay', ('localhost', 'maay')),
                ('maay --db-name maille', ('localhost', 'maille')),
                ('maay --db-host foo', ('foo', 'maay')),
                ('maay --db-host foo --db-name maille', ('foo', 'maille')),
                ]
        for cmdLine, (expectedHost, expectedDatabase) in data:
            config = NodeConfiguration()
            sys.argv = cmdLine.split()
            config.load()
            self.assertEquals(config.db_host, expectedHost)
            self.assertEquals(config.db_name, expectedDatabase)

    # XXX: there seems to be strange side-effects in l.c.configuration
    #      this test needs to be run first. This is a BUG that I
    #      could not fix easily.
    def test0FromConfigFile(self):
        config = NodeConfiguration()
        config.config_file = osp.join(osp.dirname(__file__), 'data', 'webapp1.ini')
        config.load()
        self.assertEquals(config.db_host, 'eusebius')
        self.assertEquals(config.db_name, 'maay')

    def testFromBoth(self):
        config = NodeConfiguration()
        sys.argv = 'maay --db-host truc'.split()
        config.config_file = osp.join(osp.dirname(__file__), 'data', 'webapp2.ini')
        config.load()
        self.assertEquals(config.db_host, 'truc')
        self.assertEquals(config.db_name, 'muche')

    def testFilterFilesWith(self): #XXX: what about Win32 ?
        files = ['.', '/this/should/never/be/found/to/exist']
        result = configuration._filter_files_with(files, os.R_OK)
        self.assertEquals(result, ['.'])

class ImageConfigurationTC(unittest.TestCase):
    def setUp(self):
        self.argvBackup = sys.argv

    def tearDown(self):
        sys.argv = self.argvBackup
    
    def testLoadNotClutteredByArgv(self):
        sys.argv = "indexer.py --private-index-dir=foo".split()
        config = ImageConfiguration()
        self.assertEquals(config.get('thumbnails-dir'), '.maay_thumbnails')
        
if sys.platform == 'win32':
    class Win32ConfigTC(unittest.TestCase):
        def testUpdateEnvPath(self):
            platform = sys.platform
            oldpath = os.environ['PATH']
            sys.platform = 'win32'
            try:
                configuration._update_env_path("tmp")
                envpath = os.environ['PATH']
                regexp = r'tmp[/\\]pdftohtml[:;]tmp[/\\]mysql[/\\]bin[:;]tmp[/\\]c:\antiword$'
                self.failUnless(re.search(regexp, envpath)), envpath
            finally:
                sys.platform = platform
                os.environ['PATH'] = oldpath
else:
    print "****  Skipping Win32 tests on non-windows platforms"

if __name__ == '__main__':
    unittest.main()
