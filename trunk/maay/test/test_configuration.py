"""small unit tests for Configuration class"""

import unittest
import sys
import os
import os.path as osp
import re

from maay import configuration
from maay.server import WebappConfiguration

class WebappConfigTC(unittest.TestCase):

    def testFromCommandLine(self):
        data = [('maay', ('localhost', 'maay')),
                ('maay --db-name maille', ('localhost', 'maille')),
                ('maay --db-host foo', ('foo', 'maay')),
                ('maay --db-host foo --db-name maille', ('foo', 'maille')),
                ]
        for cmdLine, (expectedHost, expectedDatabase) in data:
            config = WebappConfiguration()
            sys.argv = cmdLine.split()
            config.load()
            self.assertEquals(config.db_host, expectedHost)
            self.assertEquals(config.db_name, expectedDatabase)

    # XXX: there seems to be strange side-effects in l.c.configuration
    #      this test needs to be run first. This is a BUG that I
    #      could not fix easily.
    def test0FromConfigFile(self):
        config = WebappConfiguration()
        config.config_file = osp.join(osp.dirname(__file__), 'data', 'webapp1.ini')
        config.load()
        self.assertEquals(config.db_host, 'eusebius')
        self.assertEquals(config.db_name, 'maay')

    def testFromBoth(self):
        config = WebappConfiguration()
        sys.argv = 'maay --db-host truc'.split()
        config.config_file = osp.join(osp.dirname(__file__), 'data', 'webapp2.ini')
        config.load()
        self.assertEquals(config.db_host, 'truc')
        self.assertEquals(config.db_name, 'muche')


class Win32ConfigTC(unittest.TestCase):

    def test_update_env_path(self):
        platform = sys.platform
        oldpath = os.environ['PATH']
        sys.platform = 'win32'
        try:
            configuration._update_env_path("tmp")
            envpath = os.environ['PATH']
            regexp = r'.*[:;]tmp[/\\]antiword[:;]tmp[/\\]pdftohtml[:;]tmp[/\\]mysql[/\\]bin$'
            self.failUnless(re.match(regexp, envpath)), envpath
        finally:
            sys.platform = platform
            os.environ['PATH'] = oldpath 
            
if __name__ == '__main__':
    unittest.main()
