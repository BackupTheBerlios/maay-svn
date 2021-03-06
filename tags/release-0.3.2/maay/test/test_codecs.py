# -*- coding: iso-8859-1 -*-
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
import codecs
import gzip
import bz2
import os

class CodecsTC(unittest.TestCase):

    def setUp(self):
        f = gzip.open('toto.gz', 'wb')
        self.data = u"L'�t� au bord de la mer"
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
