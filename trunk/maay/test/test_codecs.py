
import unittest
import codecs
import gzip
import bz2
import os

class CodecsTC(unittest.TestCase):
    def test_readCompressed(self):
        f = gzip.open('toto.gz', 'wb')
        for i in range(10):
            f.write(('%d'%i)*50+'\n')
        f.close()

        c = codecs.open('toto.gz', 'rb', 'zlib_codec')
        data = c.read()
        c.close
        self.failUnless(data.startswith('0000'))

if __name__ == '__main__':
    unittest.main()
