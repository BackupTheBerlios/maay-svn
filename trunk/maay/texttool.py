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

"""this module provide text / parsing tools"""

__revision__ = '$Id$'

from HTMLParser import HTMLParser, HTMLParseError
import codecs
import re
import mimetypes
import gzip
import bz2

WORD_MIN_LEN = 2
WORD_MAX_LEN = 50
MAX_STORED_SIZE = 65535

WORDS_RGX = re.compile(r'\w{%s,%s}' % (WORD_MIN_LEN, WORD_MAX_LEN)) 



CHARSET_RGX = re.compile(r'charset=[\s"]*([^\s"]+)', re.I | re.S | re.U)
XML_ENCODING_RGX = re.compile(r'^<\?xml version=[^\s]*\s*encoding=([^\s]*)\s*\?>', re.I | re.S | re.U)

class ParsingError(Exception):
    """raised when an error occurs during the indexation of a file"""
    pass

def normalizeHtmlEncoding(htmlEncoding):
    # XXX FIXME: this function probably already exists somewhere ...
    if htmlEncoding in ('iso8859-1', 'iso-latin1', 'iso-latin-1', 'latin-1',
                        'latin1'):
        return 'ISO-8859-1'
    # default, return original one
    return htmlEncoding

def guessEncoding(filename): #may throw IOError
    """try to guess encoding from a buffer
        Bytes  	Encoding Form
        00 00 FE FF 	UTF-32, big-endian
        FF FE 00 00 	UTF-32, little-endian
        FE FF 	        UTF-16, big-endian
        FF FE 	        UTF-16, little-endian
        EF BB BF 	UTF-8
    """
    if filename.endswith(".gz"):
        stream = gzip.open(filename, 'rb')
    elif filename.endswith(".bz2"):
        stream = bz2.BZ2File(filename, 'rb')
    else:
        stream = file(filename, 'rb')
        
    try:
        buffer = stream.read(4)
        # try to guess from BOM
        if buffer[:4] in (codecs.BOM_UTF32_BE, codecs.BOM_UTF32_LE):
            return 'UTF-32'
        elif buffer[:2] in (codecs.BOM_UTF16_BE, codecs.BOM_UTF16_LE):
            return 'UTF-16'
        elif buffer[:3] == codecs.BOM_UTF8:
            return 'UTF-8'
        buffer += stream.read()
        if mimetypes.guess_type(filename)[0] == 'text/html':
            m = CHARSET_RGX.search(buffer)
            if m is not None :
                return normalizeHtmlEncoding(m.group(1))
        # check for xml encoding declaration
        if buffer.lstrip().startswith('<?xml'):
            m = XML_ENCODING_RGX.match(buffer)
            if m is not None:
                return m.group(1)[1:-1].upper()
            # xml files with no encoding declaration default to UTF-8
            return 'UTF-8'
        try:
            data = unicode(buffer, 'utf-8')
            return 'UTF-8'
        except UnicodeError:
            return 'ISO-8859-1'
    finally:
        stream.close()


def open(filename, mode='rb', encoding='ascii', errors='strict'):
    """open potentially compressed files using a codec converter"""
    if 'r' in mode:
        converter = codecs.getreader(encoding)
    elif 'w' in mode:
        converter = codecs.getwriter(encoding)
    else:
        raise ValueError("Unsupported mode '%s'" % mode)
    
    if filename.endswith('.gz'):
        opener = gzip.open
    elif filename.endswith('.bz2'):
        opener = bz2.BZ2File
    else:
        opener = file

    return converter(opener(filename, mode), errors)

class AbstractParser:
    """base-class for file parsers"""
    def parseFile(self, filename, encoding=None):
        """returns a 4-uple (title, normalized_text, links, offset)
        TODO: port original code from htmltotext
        :param encoding: if None, then need to be guessed
        """
        encoding = encoding or guessEncoding(filename)
        try:
            stream = open(filename, 'rb', encoding, errors='ignore')
        except LookupError:
            raise ParsingError('Unsupported document encoding %s' % encoding)
        try:
            return self.parseString(stream.read())
        finally:
            stream.close()

    def parseString(self, source):
        raise NotImplementedError()


class TextParser(AbstractParser):

    def parseString(self, source):
        result = source
        first_line = min(80, result.find('\n'))
        title = result[:first_line]
        return title, result, [], 0
        

class MaayHTMLParser(AbstractParser, HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.links = []
        self.textbuf = []
        self.title = ''
        self.parsingTitle = False
        self.parsingBody = False
        
    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.parsingTitle = True
        elif tag == 'a':
            attrs = dict(attrs)
            href = attrs.get('href')
            if href:
                self.links.append(href)
        elif tag == 'body':
            self.parsingBody = True
                
    def handle_endtag(self, tag):
        if tag == 'title':
            self.parsingTitle = False
        self.textbuf.append(u' ') # handle cases such as <b>titi</b><i>tutu</i>

    def handle_data(self, data):
        if self.parsingTitle:
            self.title += data
        elif self.parsingBody:
            self.textbuf.append(data)
    
    def parseString(self, source):
        try:
            self.feed(source)
        except HTMLParseError, exc:
            print "Error parsing document: %s" % exc
        result = u'\n'.join(self.textbuf)
        if not self.title:
            first_line = min(80, result.find('\n'))
            self.title = result[:first_line]
        return self.title, result, self.links, 0


class ExifParser(AbstractParser):
    """A parser for Exif information found in image files"""

    def parseString(self, source):
        return u'An image', u'The image', [], 0

        
_table = {}
for i in xrange(32):
    _table[i] = ord(' ')
del i



for s, d in zip(    list('\xc0\xc1\xc2\xc3\xc4\xc5'
    '\xc7'
    '\xc8\xc9\xca\xcb'
    '\xcc\xcd\xce\xcf'
    '\xd0'
    '\xd1'
    '\xd2\xd3\xd4\xd5\xd6\xd8'
    '\xd9\xda\xdb\xdc'
    '\xdd'
    '\xe0\xe1\xe2\xe3\xe4\xe5'
    '\xe7'
    '\xe8\xe9\xea\xeb'
    '\xec\xed\xee\xef'
    '\xf0'
    '\xf1'
    '\xf2\xf3\xf4\xf5\xf6\xf8'
    '\xf9\xfa\xfb\xfc'
    '\xff')
    ,
    list('aaaaaa'
    'c'
    'eeee'
    'iiii'
    'o'
    'n'
    'oooooo'
    'uuuu'
    'y'
    'aaaaaa'
    'c'
    'eeee'
    'iiii'
    'o'
    'n'
    'oooooo'
    'uuuu'
    'y'
    )):
    _table[ord(s)] = ord(d)

def normalizeText(text, table=_table):
    """turns everything to lowercase, and converts accentuated
    characters to non accentuated chars.

    :param text: **unicode** string to normalize
    """
    assert type(text) is unicode, "got %s instead of unicode !" % type(text)
    text = text.translate(table).lower()
    return ' '.join(text.split())

del _table


def untagText(text):
    """remove every tag in <text>
    >>> text = <a href="...">hello <b>world</b></a>
    >>> untagText(text)
    hello world
    """
    rgx = re.compile('<.*?>')
    return rgx.sub('', text)

_table2 = {}
for i in range(0x20) + range(0xD800,0xE000) + [0xFFFE, 0xFFFF]:
    _table2[i] = None
for i in (0x9, 0xA, 0xD):
    del _table2[i]
del i

    
def removeControlChar(text, table= _table2):
    """remove control characters which are not allowed in XML 1.0"""
    # This is required to prevent internal errors in the xmlrpc server
    assert type(text) is unicode, "got %s instead of unicode !" % type(text)
    return text.translate(table)
del _table2
    

def makeAbstract(text, words):
    """return the original text with HTML emphasis tags
    around <words> occurences
    XXX: this is a quick and dirty implementation
    """
    rgx = re.compile('|'.join(words), re.I)
    text = untagText(text)
    buf = []
    size = 0
    for occurence in rgx.finditer(text):
        wordFound = occurence.group(0)
        start, end = occurence.start(), occurence.end()
        before = text[start-30:start-1]
        after = text[end+1:end+30]
        size += len(wordFound) + 60
        buf.append('%s <b>%s</b> %s' % (before, wordFound, after))
        if size >= 200:
            break
    else:
        # case where we have less than 200 characters to display
        return text[:200]
    return u' <b>[...]</b> '.join(buf)
