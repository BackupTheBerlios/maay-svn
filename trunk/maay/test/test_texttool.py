# -*- coding: ISO-8859-1 -*-
"""unit tests for Text and HTML parsers"""

import unittest
from os.path import join, dirname

from maay.texttool import MaayHTMLParser, guessEncoding

ROW_TEXT = u"foo été bar baz top bim bam boum"

SIMPLE_HTML = u"""<html>
<head><title>maille Maay</title></head>
<body>Hello été world
This is <a href="something.com">a link</a>
and this is <a href="somethingelse.com">another link</a>
</body>
</html>
"""

DATADIR = join(dirname(__file__), 'data')

class HTMLParserTC(unittest.TestCase):

    def setUp(self):
        self.parser = MaayHTMLParser()

    def testParseRaw(self):
        html = '<body>%s</body>' % ROW_TEXT
        title, text, links, offset = self.parser.parseString(html)
        self.assertEquals(title, '')
        self.assertEquals(text, ROW_TEXT.replace(u'é', 'e'))
        self.assertEquals(links, [])

    def testParseSimpleHtml(self):
        title, text, links, offset = self.parser.parseString(SIMPLE_HTML)
        self.assertEquals(title, 'maille Maay')
        self.assertEquals(text, 'hello ete world this is a link and this is another link')
        self.assertEquals(links, ['something.com', 'somethingelse.com'])
    

    def testParseHtmlFileWithEncoding(self):
        filename = join(DATADIR, 'encoded.html')
        title, text, links, offset = self.parser.parseFile(filename, 'iso-8859-1')
        self.assertEquals(title, 'maille Maay')
        self.assertEquals(text, 'hello ete world this is a link and this is another link')
        self.assertEquals(links, ['something.com', 'somethingelse.com'])
        
    def testParseHtmlFileAndGuessEncoding(self):
        filename = join(DATADIR, 'encoded.html')
        title, text, links, offset = self.parser.parseFile(filename)
        self.assertEquals(title, 'maille Maay')
        self.assertEquals(text, 'hello ete world this is a link and this is another link')
        self.assertEquals(links, ['something.com', 'somethingelse.com'])
        
    def testGuessEncoding(self):
        self.assertEquals(guessEncoding(join(DATADIR, 'utf8.txt')), 'UTF-8')
        self.assertEquals(guessEncoding(join(DATADIR, 'utf16.txt')), 'UTF-16')
        # self.assertEquals(guessEncoding(join(DATADIR, 'utf16be.txt')), 'UTF-16')
        self.assertEquals(guessEncoding(join(DATADIR, 'utf32.txt')), 'UTF-32')
        # self.assertEquals(guessEncoding(join(DATADIR, 'utf32be.txt')), 'UTF-32')
        self.assertEquals(guessEncoding(join(DATADIR, 'latin1.xml')), 'ISO-8859-1')
        self.assertEquals(guessEncoding(join(DATADIR, 'utf8.xml')), 'UTF-8')
        self.assertEquals(guessEncoding(join(DATADIR, 'latin1.xml')), 'ISO-8859-1')
        self.assertEquals(guessEncoding(join(DATADIR, 'encoded.html')), 'ISO-8859-1')

    def test_normalizeHTMLEncoding(self):
        data = [
            'latin1', 'ISO-8859-1',
            'iso-88591', 'ISO-8859-1',
            
            ]

    def test_parseDifficultFile(self):
        filename = join(DATADIR, 'node22.html')
        title, text, links, offset = self.parser.parseFile(filename)
        self.assertEquals(type(text), unicode)

if __name__ == '__main__':
    unittest.main()
