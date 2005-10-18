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

"""this module handles Converter Registry

Typical use ::

    >>> from maay.converter import extractWordsFromFile
    >>> title, text, links, offset = extractWordsFromFile('foo.pdf')
    >>> title, text, links, offset = extractWordsFromFile('foo.doc')

To define a new command-based converter, just extend the
CommandBasedConverter class and define MIME_TYPE and
optionally OUTPUT_TYPE variables ::

    from maay import converter
    class MyPDFConverter(converter.CommandBasedConverter):
        MIME_TYPE = 'application/pdf'
        OUTPUT_TYPE = 'text'
        COMMAND = 'mypdfconverter %(input)s -o %(output)s'

and that's it. Next time the indexer will try to index a PDF file,
it will use your converter.

"""
__revision__ = '$Id$'

# TODO: add support for xls, ppt,  openoffice, mp3, ogg

# XXX: need to handle file encodings

import os
from mimetypes import guess_type, types_map
from tempfile import mkdtemp
import gzip
import bz2

from maay.texttool import TextParser, ExifParser, MaayHTMLParser as HTMLParser, ParsingError

# REGISTRY is a mimetype / converterList map
REGISTRY = {}

class IndexationFailure(Exception):
    """raised when an indexation has failed"""

class MetaConverter(type):
    """a simple metaclass for automatic converter registration"""
    def __new__(cls, classname, bases, classdict):
        klass = type.__new__(cls, classname, bases, classdict)
        mimetype = classdict.get('MIME_TYPE')
        if mimetype:
            # insert user-defined converter first
            REGISTRY.setdefault(mimetype, []).insert(0, klass)
        return klass


class BaseConverter:
    """base converter class"""
    __metaclass__ = MetaConverter
    OUTPUT_TYPE = 'text'
    # None means "let the text parser guess the encoding"
    OUTPUT_ENCODING = None

    def getParser(self):
        raise NotImplementedError()

    def extractWordsFromFile(self, filename):
        """entry point of each converter class

        :returns: a word-vector
        """
        parser = self.getParser()
        try:
            return parser.parseFile(filename, self.OUTPUT_ENCODING)
        except ParsingError, exc:
            raise IndexationFailure("Cannot index document %s (%s)" % (filename, exc))


class RawTextConverter(BaseConverter):
    """provides simple text parser"""
    OUTPUT_TYPE = 'text'
    MIME_TYPE = 'text/plain'

    def getParser(self):
        return TextParser()
        
class HTMLConverter(BaseConverter):
    """provides a simple HTML parser"""
    OUTPUT_TYPE = 'html'
    MIME_TYPE = 'text/html'

    def getParser(self):
        return HTMLParser()

class ImageBasedConverter(BaseConverter):
    """provides base Image converter
       In the future, it may hold EXIF information retrieval methods"""
    OUTPUT_TYPE = 'image'

    def getParser(self):
        return ExifParser ()

class JpegConverter(ImageBasedConverter):
    OUTPUT_TYPE = 'jpeg'
    MIME_TYPE = 'image/jpeg'

class CommandBasedConverter(BaseConverter):
    COMMAND = None

    def extractWordsFromFile(self, filename):
        outputDir = mkdtemp()
        if filename.endswith('.gz'):
            opener = gzip.open
        elif filename.endswith('.bz2'):
                opener = bz2.BZ2File
        else:
            opener = file
            
        compressed = opener(filename, 'rb')
        uncompressedFile = os.path.join(outputDir, 'uncompressed')
        uncompressed = file(uncompressedFile, 'wb')
        uncompressed.write(compressed.read())
        compressed.close()
        uncompressed.close()

            
        outputFile = os.path.join(outputDir, 'outfile')
        command_args = {'input' : uncompressedFile, 'output' : outputFile}
        cmd = self.COMMAND % command_args
        #print "Executing %r" % cmd
        errcode = os.system(cmd)
        try:
            if errcode == 0: # OK
                parser = self.getParser()
                return parser.parseFile(outputFile, self.OUTPUT_ENCODING)
            else:
                raise IndexationFailure('Unable to index %r' % filename)
        finally:
            if os.path.isfile(outputFile):
                os.remove(outputFile)
            if os.path.isfile(uncompressedFile):
                os.remove(uncompressedFile)
            os.rmdir(outputDir)


class PDFConverter(CommandBasedConverter, HTMLConverter):
    COMMAND = 'pdftohtml -i -q -noframes -stdout -enc UTF-8 "%(input)s" > "%(output)s"'
    OUTPUT_TYPE = 'html'
    MIME_TYPE = 'application/pdf'
    OUTPUT_ENCODING = 'UTF-8'

class PSConverter(CommandBasedConverter, RawTextConverter):
    COMMAND = 'ps2ascii "%(input)s" "%(output)s"'
    MIME_TYPE = 'application/postscript'

class RTFConverter(CommandBasedConverter, RawTextConverter):
    COMMAND = 'unrtf --html "%(input)s" > "%(output)s"'
    OUTPUT_TYPE = 'html'
    MIME_TYPE = 'text/rtf'

class MSWordConverter(CommandBasedConverter):
    COMMAND = 'antiword "%(input)s" > "%(output)s"'
    MIME_TYPE = 'application/msword'

def extractWordsFromFile(filename):
    mimetype = guess_type(filename)[0]
    converters = REGISTRY.get(mimetype, [])
    for klass in converters:
        try:
            converter = klass()
            return converter.extractWordsFromFile(filename)
        except IndexationFailure, exc:
            print "indexation failed for %s, trying another converter" % filename
            continue
    raise IndexationFailure("Could not index file %r" % filename)

def isKnownType(filename):
    mimetype = guess_type(filename)[0]
    return mimetype in REGISTRY
