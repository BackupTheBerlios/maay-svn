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

"""tests converters registry management"""

import unittest
from mimetypes import guess_type

from maay import converter

class ConvertersTC(unittest.TestCase):
    
    def testRegistry(self):
        """tests that converters we get match filenames's mimetype"""
        filenames = ['foo.pdf', 'foo.ps', 'foo.html', 'foo.txt',
                     'foo.doc', 'foo.rtf']
        for filename in filenames:
            mimetype = guess_type(filename)[0]
            if mimetype is None:
                print "Your config can't guess %s 's filetype" % filename
                continue
            converters = converter.REGISTRY[mimetype]
            for klass in converters:
                self.assertEquals(klass.MIME_TYPE, mimetype)

    def testLowLevelRegistry(self):
        """tests predefined converters registration"""
        self.assert_(converter.RawTextConverter in converter.REGISTRY['text/plain'])
        self.assert_(converter.HTMLConverter in converter.REGISTRY['text/html'])
        self.assert_(converter.RTFConverter in converter.REGISTRY['text/rtf'])
        self.assert_(converter.PSConverter in converter.REGISTRY['application/postscript'])
        self.assert_(converter.PDFConverter in converter.REGISTRY['application/pdf'])
        self.assert_(converter.MSWordConverter in converter.REGISTRY['application/msword'])

    def testCustomizedConverter(self):
        """make sure a user can define its own converter"""
        original_converters = list(converter.REGISTRY.get('application/pdf', []))
        class MyConverter(converter.CommandBasedConverter):
            COMMAND = "mypdfindexer %(input)s %(output)s"
            MIME_TYPE = 'application/pdf'
        new_converters = converter.REGISTRY.get('application/pdf', [])
        self.assertEquals(new_converters, [MyConverter] + original_converters)

    def testIndexationFailure(self):
        self.assertRaises(converter.IndexationFailure, converter.extractWordsFromFile,
                          'AUTHORS')

if __name__ == '__main__':
    unittest.main()
