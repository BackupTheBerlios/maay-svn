# -*- coding: ISO-8859-1 -*-
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
MAX_STORED_SIZE = 65535 # not actually used in the code for now,
                        # because the db engine does the truncation
                        # for us

WORDS_RGX = re.compile(r'\w{%s,%s}' % (WORD_MIN_LEN, WORD_MAX_LEN)) 



CHARSET_RGX = re.compile(r'charset=[\s"]*([^\s"]+)', re.I | re.S | re.U)
XML_ENCODING_RGX = re.compile(r'^<\?xml version=[^\s]*\s*encoding=([^\s]*)\s*\?>', re.I | re.S | re.U)

class ParsingError(Exception):
    """raised when an error occures during the indexation of a file"""
    pass

def normalizeHtmlEncoding(htmlEncoding):
    # XXX FIXME: this function probably already exists somewhere ...
    if htmlEncoding in ('iso8859-1', 'iso-latin1', 'iso-latin-1', 'latin-1',
                        'latin1'):
        return 'ISO-8859-1'
    # default, return original one
    return htmlEncoding


def guessEncoding(filename):
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
        result = normalizeText(source)
        title = result[:60]
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
        result = normalizeText(u''.join(self.textbuf))
        return self.title, result, self.links, 0


        
from string import maketrans
_table = maketrans(
    ''.join([chr(i) for i in xrange(32)]) + 
    '\xc0\xc1\xc2\xc3\xc4\xc5'
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
    '\xff'
    ,
    ' ' * 32 +
    'aaaaaa'
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
    )
_table = [ord(c) for c in _table]
del maketrans

def normalizeText(text, table=_table):
    """turns everything to lowercase, and converts accentuated
    characters to non accentuated chars.

    :param text: **unicode** string to normalize
    """
    assert type(text) is unicode
    text = text.lower().translate(table)
    return ' '.join(text.split())

del _table
