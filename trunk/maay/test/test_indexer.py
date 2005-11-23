#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify it
#     under the terms of the GNU General Public License as published by the
#     Free Software Foundation; either version 2 of the License, or (at your
#     option) any later version.
#     
#     This program is distributed in the hope that it will be useful, but
#     WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
#     Public License for more details.
#     
#     You should have received a copy of the GNU General Public License along
#     with this program; if not, write to the Free Software Foundation, Inc.,
#     59 Temple Place - Suite 330, Boston, MA 02111-1307 USA.
#     

__revision__ = '$Id$'

import unittest
from  tempfile import mkstemp
import os

from maay.indexer import *
from maay import indexer

class GlobalFunctionTC(unittest.TestCase):

    def testMakeDocumentId(self):
        handle, filename = mkstemp()
        f = os.fdopen(handle, 'wb')
        data = '0'*128 + '\n' * 1000
        f.write(data)
        f.close()
        self.assertEquals(makeDocumentId(filename), sha.sha(data).hexdigest())
        os.remove(filename)

#     def testMimetypeUpdate(self):
#         #XXX: This may need to go away since we provide converters for python
#         # and the type_map update in indexer is not sufficient to catch python files
#         # as text files
#         self.assertEquals('text/plain', mimetypes.types_map['.py'])
        

class DummyThread:
    alive = False
    def isAlive(self):
        return self.alive

class ThreadsTC(unittest.TestCase):

    def tearDown(self):
        indexer.indexer_thread = None
        
    def test_is_running(self):
        self.failIf(is_running())
        indexer.indexer_thread = DummyThread()
        self.failIf(is_running())
        indexer.indexer_thread.alive = True
        self.failUnless(is_running())

    
        

if __name__ == '__main__':
    unittest.main()
