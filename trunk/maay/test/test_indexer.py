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
        
        

if __name__ == '__main__':
    unittest.main()
