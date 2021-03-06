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

"""unit tests for Text and HTML parsers"""

__revision__ = '$Id$'


import unittest
from os.path import join, dirname

from maay.texttool import MaayHTMLParser, TextParser, guessEncoding, \
     universalOpen, untagText, normalizeText, removeControlChar, makeAbstract, \
     LStringIO

RAW_TEXT = u"foo �t� bar baz top bim bam boum"

SIMPLE_HTML = u"""<html>
<head><title>maille Maay</title></head>
<body>Hello �t� world
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
                          RAW_TEXT.replace(u'�', 'e'))
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

    def _test_parseDifficultFile(self):
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
        self.failUnless(u'ent�te' in data)
        
    def testBz2(self):
        f = universalOpen(join(DATADIR, 'compressed_bzip2.txt.bz2'), 'rb', 'utf-8')
        data = f.read()
        f.close()
        self.assertEquals(type(data), unicode)
        self.failUnless(u'ent�te' in data)

class UtilitiesTC(unittest.TestCase):
    def testUntag(self):
        text = 'Hello <a href="foo.bar.com">world <b>!</b></a><img alt="" />'
        self.assertEquals(untagText(text), 'Hello world !')

    def testNormalizeText(self):
        text = u"� Paris,\t\x02l'�t� \nsera   chaud"
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

    def testBasicLStringIO(self):
        buf = LStringIO()
        buf.write('foo')
        buf.write('bar')
        self.assertEquals(buf.getvalue(), 'foobar')
        buf.write(u'baz')
        self.assertEquals(buf.getvalue(), 'foobarbaz')

    def testLStringIOWithUnicodeStrings(self):
        buf = LStringIO()
        buf.write(unicode('�t�', 'iso-8859-1'))
        buf.write('foo')
        buf.write(u'bar')
        self.assertEquals(buf.getvalue(), unicode('�t�foobar', 'iso-8859-1'))
        buf.write(u'baz')
        self.assertEquals(buf.getvalue(), unicode('�t�foobarbaz', 'iso-8859-1'))



class AbstractTC(unittest.TestCase):
    text = "This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA"

    def testSimple(self):
        # Check excerpt at the beginning of the text

        abstract = makeAbstract(self.text, [u"free"])
        expected = u'This program is <b>free</b> software; you can redistribute it and/or modify it under the terms of <b>...</b>  Public License as published by the <b>Free</b> Software Foundation; either version 2 of the License, or (at your <b>...</b>  this program; if not, write to the <b>Free</b> Software Foundation, Inc., 51 <b>...</b>'
        self.assertEquals(expected, abstract)

    def testMixedCase(self):
        abstract = makeAbstract(self.text, [u"pUrPoSe"])
        expected = ' <b>...</b>  or FITNESS FOR A PARTICULAR <b>PURPOSE</b>.  See the GNU General Public <b>...</b>'
        self.assertEquals(expected, abstract)

    def testUnknownWord(self):
        abstract = makeAbstract(self.text, [u"FOOBAR"])
        expected = 'This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, <b>...</b>'
        self.assertEquals(expected, abstract)

    def testWordAtEnd(self):
        abstract = makeAbstract(self.text, [u"Boston"])
        expected = ' <b>...</b>  Inc., 51 Franklin St, Fifth Floor, <b>Boston</b>, MA  02110-1301 USA'
        self.assertEquals(expected, abstract)

    def testLength200AndUnknownWord(self):
        try:
            abstract = makeAbstract(self.text[:200], [u'tralala'])
        except IndexError:
            self.fail('bug #5648 is present')


if __name__ == '__main__':
    unittest.main()

