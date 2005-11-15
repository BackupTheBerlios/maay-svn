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

import unittest
from  tempfile import mkstemp
import os

from maay.indexer import *

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
        
        

if __name__ == '__main__':
    unittest.main()
