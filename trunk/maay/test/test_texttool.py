# -*- coding: iso-8859-1 -*-
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

"""unit tests for Text and HTML parsers"""



import unittest
from os.path import join, dirname

from maay.texttool import MaayHTMLParser, TextParser, guessEncoding, \
     universalOpen, untagText, normalizeText, removeControlChar

RAW_TEXT = u"foo été bar baz top bim bam boum"

SIMPLE_HTML = u"""<html>
<head><title>maille Maay</title></head>
<body>Hello été world
This is <a href="something.com">a link</a>
and this is <a href="somethingelse.com">another link</a>
</body>
</html>
"""

DATADIR = join(dirname(__file__), 'data')


class TextParserTC(unittest.TestCase):

    def setUp(self):
        self.parser = TextParser()

    def testTitleGuess(self): #XXX: complete this with PDF/PS files before commit time !!!
        """Make sure the title is the filename when we treat a text file
           or no title could be found
        """
        title, text, links, offset = self.parser.parseFile(join(DATADIR, 'latin1.txt'), 'latin1.txt', 'ISO-8859-1')
        self.assertEquals(title, 'latin1.txt')
        self.assertEquals(normalizeText(text), "c'est l'ete")
        self.assertEquals(links, [])
        # Now, PS file
        title, text, links, offset = self.parser.parseFile(join(DATADIR, 'utf8.ps'), 'utf8.ps', 'UTF-8')
        self.assertEquals(title, 'utf8.ps')
        self.assertEquals(links, [])
        # The PDF (yes, it's important to test this too)
        title, text, links, offset = self.parser.parseFile(join(DATADIR, 'utf8.pdf'), 'utf8.pdf', 'UTF-8')
        self.assertEquals(title, 'utf8.pdf')
        self.assertEquals(links, [])


class HTMLParserTC(unittest.TestCase):

    def setUp(self):
        self.parser = MaayHTMLParser()

    def testParseRaw(self):
        html = '<body>%s</body>' % RAW_TEXT
        title, text, links, offset = self.parser.parseString(html)
        # parseString() should return empty title when non available in the HTML
        self.assertEquals(title, '')
        self.assertEquals(normalizeText(text),
                          RAW_TEXT.replace(u'é', 'e'))
        self.assertEquals(links, [])

    def testTitleGuess(self):
        """Make sure the title is the filename when we treat a text file
           or no title could be found
        """
        title, text, links, offset = self.parser.parseFile(join(DATADIR, "notitle.html"), 'notitle.html')
        self.assertEquals(title, 'notitle.html')
        self.assertEquals(normalizeText(text), "maille maay")
        self.assertEquals(links, [])


    def testParseSimpleHtml(self):
        title, text, links, offset = self.parser.parseString(SIMPLE_HTML)
        self.assertEquals(title, 'maille Maay')
        self.assertEquals(normalizeText(text),
                          'hello ete world this is a link and this is another link')
        self.assertEquals(links, ['something.com', 'somethingelse.com'])
    

    def testParseHtmlFileWithEncoding(self):
        filename = join(DATADIR, 'encoded.html')
        title, text, links, offset = self.parser.parseFile(filename, 'encoded.html', 'iso-8859-1')
        self.assertEquals(title, 'maille Maay')
        self.assertEquals(normalizeText(text),
                          'hello ete world this is a link and this is another link')
        self.assertEquals(links, ['something.com', 'somethingelse.com'])
        
    def testParseHtmlFileAndGuessEncoding(self):
        filename = join(DATADIR, 'encoded.html')
        title, text, links, offset = self.parser.parseFile(filename, 'encoded.html')
        self.assertEquals(title, 'maille Maay')
        self.assertEquals(normalizeText(text),
                          'hello ete world this is a link and this is another link')
        self.assertEquals(links, ['something.com', 'somethingelse.com'])
        
    def test_normalizeHTMLEncoding(self):
        data = [
            'latin1', 'ISO-8859-1',
            'iso-88591', 'ISO-8859-1',
            
            ]

    def test_parseDifficultFile(self):
        """test_parseDifficultFile: This test fails for now"""
        # This file has got some weird, non HTML compliant content
        # and is not handled properly by HTMLParser 
        stream = file(join(DATADIR, 'node22.html'))
        data = stream.read()
        stream.close()
        title, text, links, offset = self.parser.parseString(data)
        self.assertEquals(title, u'21 Porting to Python 2.3')
        self.failUnless(len(text)>10)
        

class GuessEncofingTC(unittest.TestCase):
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

    def test_guessEncodingRawUTF8Text(self):
        filename = join(DATADIR, 'guess_encoding.txt')
        enc = guessEncoding(filename)
        self.assertEquals(enc, 'UTF-8')


class OpenTC(unittest.TestCase):
    def testGzip(self):
        f = universalOpen(join(DATADIR, 'compressed_gzip.txt.gz'), 'rb', 'utf-8')
        data = f.read()
        f.close()
        self.assertEquals(type(data), unicode)
        self.failUnless(u'entête' in data)
        
    def testBz2(self):
        f = universalOpen(join(DATADIR, 'compressed_bzip2.txt.bz2'), 'rb', 'utf-8')
        data = f.read()
        f.close()
        self.assertEquals(type(data), unicode)
        self.failUnless(u'entête' in data)

class UtilitiesTC(unittest.TestCase):
    def testUntag(self):
        text = 'Hello <a href="foo.bar.com">world <b>!</b></a><img alt="" />'
        self.assertEquals(untagText(text), 'Hello world !')

    def testNormalizeText(self):
        text = u"À Paris,\t\x02l'été \nsera   chaud"
        norm = normalizeText(text)
        self.assertEquals(u"a paris, l'ete sera chaud", norm)
        self.assertEquals(unicode, type(norm))
        
    def testRemoveControlChar(self):
        text = u''.join([chr(i) for i in range(32)])
        text += u'\uFFEF\uFFFE\uFFFF'
        text += u'\uDA00toto\U00011234'
        norm = removeControlChar(text)
        self.assertEquals(u"\t\n\r\uFFEFtoto\U00011234", norm)
        self.assertEquals(unicode, type(norm))

if __name__ == '__main__':
    unittest.main()
