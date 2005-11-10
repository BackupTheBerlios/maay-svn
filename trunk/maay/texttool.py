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
__metaclass__ = type

from HTMLParser import HTMLParser, HTMLParseError
import codecs
import re
import sys
import mimetypes
import gzip
import bz2

from maay.image import get_ustring_from_exif, make_thumbnail
from maay.configuration import ImageConfiguration as ImConfig


WORD_MIN_LEN = 2
WORD_MAX_LEN = 50

MAX_EXCERPT = 5
EXCERPT_MAX_LEN = 70

MAX_STORED_SIZE = 65535

WORDS_RGX = re.compile(r'\w{%s,%s}' % (WORD_MIN_LEN, WORD_MAX_LEN)) 

CHARSET_RGX = re.compile(r'charset=[\s"]*([^\s"]+)', re.I | re.S | re.U)
XML_ENCODING_RGX = re.compile(r'^<\?xml version=[^\s]*\s*encoding=([^\s]*)\s*\?>', re.I | re.S | re.U)


class LStringIO(list):
    """simple StringIO-like objects using a list
       Note: LStringIO should be more or less equivalent to cStrinIO speed-wise
       but has the great advantage to accept any unicode string
    """
    def __init__(self):
        list.__init__(self)

    write = list.append

    def getvalue(self):
        return u''.join(self)

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
        Bytes           Encoding Form
        00 00 FE FF     UTF-32, big-endian
        FF FE 00 00     UTF-32, little-endian
        FE FF           UTF-16, big-endian
        FF FE           UTF-16, little-endian
        EF BB BF        UTF-8
    """

    if filename.endswith(".gz"):
        stream = gzip.open(filename, 'rb')
    elif filename.endswith(".bz2"):
        stream = bz2.BZ2File(filename, 'rb')
    else:
        stream = file(filename, 'rb')
        
    try:
        buffer_ = stream.read(4)
        # try to guess from BOM
        if buffer_[:4] in (codecs.BOM_UTF32_BE, codecs.BOM_UTF32_LE):
            return 'UTF-32'
        elif buffer_[:2] in (codecs.BOM_UTF16_BE, codecs.BOM_UTF16_LE):
            return 'UTF-16'
        elif buffer_[:3] == codecs.BOM_UTF8:
            return 'UTF-8'
        buffer_ += stream.read()
        if mimetypes.guess_type(filename)[0] == 'text/html':
            m = CHARSET_RGX.search(buffer_)
            if m is not None :
                return normalizeHtmlEncoding(m.group(1))
        # check for xml encoding declaration
        if buffer_.lstrip().startswith('<?xml'):
            m = XML_ENCODING_RGX.match(buffer_)
            if m is not None:
                return m.group(1)[1:-1].upper()
            # xml files with no encoding declaration default to UTF-8
            return 'UTF-8'
        try:
            _ = unicode(buffer_, 'utf-8')
            return 'UTF-8'
        except UnicodeError:
            return 'ISO-8859-1'
    finally:
        stream.close()


def universalOpen(filename, mode='rb', encoding='ascii', errors='strict'):
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

    def parseFile(self, filepath, pristineFilename, encoding=None):
        """returns a 4-uple (title, normalized_text, links, offset)
        TODO: port original code from htmltotext
        :param encoding: if None, then need to be guessed
        
        When a title cannot be computed from file content,
        the last component of the filepath is used instead
        """
        try:
            encoding = encoding or guessEncoding(filepath)
            stream = universalOpen(filepath, 'rb', encoding, errors='ignore')
        except LookupError:
            raise ParsingError('Unsupported document encoding %s' % encoding)
        try:
            title, result, links, offset = self.parseString(stream.read())
            if not title:
                title = unicode(pristineFilename, sys.getfilesystemencoding()) 
            return title, result, links, offset 
        finally:
            stream.close()

    def parseString(self, source):
        """returns a 4-uple (title, normalized_text, links, offset)
           to parseFile
           When a title cannot be computed from file content parseFile
           expects an empty unicode string
        """
        raise NotImplementedError()


class TextParser(AbstractParser):

    def parseString(self, source):
        return u'', source, [], 0
        

class MaayHTMLParser(AbstractParser, HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.links = []
        self.textbuf = []
        self.title = u''
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
            print "MaayHTMLParser parseString : Error parsing document: %s" % exc
        result = u'\n'.join(self.textbuf)
        #XXX: wacky hack to get a correct title when we just processed
        #     a file from PDFTOHTML
        if self.title[-7:len(self.title)] == '.pdf-in':
            self.title = u''
        return self.title, result, self.links, 0



class ExifParser(AbstractParser):
    """A parser for Exif information found in image files"""

    def __init__(self):
        self.thumbnails_dir = None

    def get_thumbnails_dir(self):
        if not self.thumbnails_dir:
            self.thumbnails_dir = ImConfig().get_thumbnails_dir()
        return self.thumbnails_dir

    def parseFile(self, filepath, pristineFilename, encoding=None):
        """returns a 4-uple (title, normalized_text, links, offset)
        TODO: port original code from htmltotext
        :param encoding: if None, then need to be guessed
        """
        title = unicode(pristineFilename, sys.getfilesystemencoding())
        try:
            result = 'EXIF : ' + get_ustring_from_exif(filepath)
            try:
                thumb = make_thumbnail(filepath, self.get_thumbnails_dir())
            except Exception, e:
                print "Can't make thumbnail. Cause : %s" % e
                thumb = None
            return title, result, [thumb], 0
        except Exception, e:
            print "No EXIF nor thumbnails. Cause : %s" % e
        return title, u'No EXIF information available', [], 0

        
_table = {}
for i in xrange(32):
    _table[i] = ord(' ')
del i



for _s, _d in zip(    list('\xc0\xc1\xc2\xc3\xc4\xc5'
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
    _table[ord(_s)] = ord(_d)

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
    
# function do not work with unicode, TODO: fix it...
# (use for remove extra space in text before saving it in the database)
# desactivated...
def removeSpace(text):
    return text
    rgx = re.compile('\s+')
    s = LStringIO()
    lastStart = 0
    end = 0
    for occurence in rgx.finditer(text):
        start, end = occurence.start(), occurence.end()
        if start > 0:
            s.write(" ")
        s.write("%s" % text[lastStart:start])
        lastStart = end

    s.write(text[end:])
    return s.getvalue()


def boldifyText(text, words):
    rgx = re.compile('|'.join(words), re.I)
    s = LStringIO()
    lastStart = 0
    end = 0
    for occurence in rgx.finditer(text):
        wordFound = occurence.group(0)
        start, end = occurence.start(), occurence.end()
        s.write(text[lastStart:start])
        s.write(u"<b>%s</b>" % wordFound)
        lastStart = end

    s.write(text[end:])
    return u"%s" % s.getvalue()

    

def computeExcerptPositions(text, words):
    # quick and dirty regex...
    rgx = re.compile(r'\W' + r'\W|\W'.join(words) + r'\W', re.I)

    # Get the best excerpt for the abstract :
    # - excerpt for most words of the query
    # - first occurence of words
    #   - would be even better : enough occurences (if available)
    #     to fill a handful of lines

    # wordOccurrences[word] = #nb of occurences
    wordOccurrences = {}

    # excerptPositions = [(word,position)]
    excerptPositions = []

    for occurence in rgx.finditer(text):
        foundWord = occurence.group(0)
        start = occurence.start()

        if len(excerptPositions) >= MAX_EXCERPT:
            # remove one of excerpts which is the more frequent
            max_occurence = 0
            for word, occurence in wordOccurrences.items():
                max_occurence = max(occurence, max_occurence)

            if wordOccurrences.get(foundWord) == max_occurence:
                continue
                    
            for i in xrange(len(excerptPositions) - 1, 0, -1):
                word, _ = excerptPositions[i]
                if wordOccurrences[word] == max_occurence:
                    wordOccurrences[word] -= 1
                    if wordOccurrences[word] == 0:
                        del wordOccurrences[word]
                    del excerptPositions[i]

        if wordOccurrences.has_key(foundWord):
            wordOccurrences[foundWord] += 1
        else:
            wordOccurrences[foundWord] = 1

        excerptPositions.append((foundWord, start))

        if len(wordOccurrences) >= MAX_EXCERPT or \
               (len(wordOccurrences) == len(words) and \
                len(excerptPositions) == MAX_EXCERPT):
            break

    return excerptPositions


def makeAbstract(text, words):
    """return excerpts of the original text surrounding the word occurrences
    XXX: this is a less quick and dirty implementation
    """
    text = untagText(text)
    excerptPositions = computeExcerptPositions(text, words)

    text_length = len(text)

    EXCERPT_MAX_HALF_LEN = EXCERPT_MAX_LEN / 2

    if not excerptPositions:
        if text_length >= 200:
            end = 200
            while text[end].isalpha(): end -= 1
            return text[:end] + " <b>...</b>"
        else:
            return text

    s = LStringIO()
    start = -1
    last_position = -100
    last_word = 0

    for word, position in excerptPositions:
        # merge snippets if they overlap
        if position - last_position < EXCERPT_MAX_HALF_LEN:
            last_position = position
            last_word = word
            continue

        # in the general case (not first word)
        if start !=-1:
            end = last_position + EXCERPT_MAX_LEN + len(last_word)
            if end >= text_length: # address EOT
                end = text_length
            else:
                while text[end].isalpha():
                    end -= 1

            if start > 0:
                s.write(u" <b>...</b> ")
            s.write(boldifyText(text[start:end], words))
            
        start = position - EXCERPT_MAX_HALF_LEN
        if start < 0: # address begining OT
            start = 0
        else:
            while text[start].isalpha():
                start += 1

        last_position = position
        last_word = word


    if start > 0:
        s.write(u" <b>...</b> ")
    end = last_position + EXCERPT_MAX_HALF_LEN + len(word)
    if end >= text_length:
        end = text_length
    else:
        while text[end].isalpha():
            end -= 1
    s.write(boldifyText(text[start:end], words))

    if end < text_length:
        s.write(u" <b>...</b>")

    return s.getvalue()
