# -*- coding: iso-8859-1 -*-
import unittest
import codecs
import gzip
import bz2
import os

class CodecsTC(unittest.TestCase):

    def setUp(self):
        f = gzip.open('toto.gz', 'wb')
        self.data = u"L'été au bord de la mer"
        f.write(self.data.encode('utf-8'))
        f.close()

    def tearDown(self):
        os.remove("toto.gz")
        
##     def test_readCompressedWithCodec(self):
##         c = codecs.open('toto.gz', 'rb', 'zlib_codec')
##         data = c.read()
##         c.close()
##         self.assertEquals(data, self.data.encode('utf-8'))

    def test_readCompressedWithGzip(self):
        c = gzip.open('toto.gz', 'rb')
        data = c.read()
        c.close()
        self.assertEquals(data, self.data.encode('utf-8'))

    def test_readCompressedWithGzipDecoded(self):
        c = gzip.open('toto.gz', 'rb')
        reader = codecs.getreader('utf-8')
        f = reader(c)
        data = f.read()
        f.close()
        self.assertEquals(data, self.data)

if __name__ == '__main__':
    unittest.main()
