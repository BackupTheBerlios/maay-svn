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

if __name__ == '__main__':
    unittest.main()
