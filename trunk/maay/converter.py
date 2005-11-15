#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""this module handles Converter Registry

Typical use ::

    >>> from maay.converter import extractWordsFromFile
    >>> title, text, links, offset = extractWordsFromFile('foo.pdf')
    >>> title, text, links, offset = extractWordsFromFile('foo.doc')

To define a new command-based converter, just extend the
CommandBasedConverter class and define MIME_TYPES and
optionally OUTPUT_TYPE variables ::

    from maay import converter
    class MyPDFConverter(converter.CommandBasedConverter):
        MIME_TYPES = ('application/pdf',)
        OUTPUT_TYPE = 'text'
        COMMAND = 'mypdfconverter %(input)s -o %(output)s'

and that's it. Next time the indexer will try to index a PDF file,
it will use your converter.

"""
__revision__ = '$Id$'

# TODO: add support for xls, ppt,  openoffice, mp3, ogg

# XXX: need to handle file encodings

import os, os.path as osp
from mimetypes import guess_type, types_map
from tempfile import mkdtemp
import gzip
import bz2

from maay.texttool import TextParser, ExifParser, MaayHTMLParser as HTMLParser, ParsingError

# REGISTRY is a mimetype / converterList map
REGISTRY = {}

types_map.update ({
    '.conf': 'text/plain',
    '.flac':  'audio/x-flac',
    '.diff': 'application/x-executable',
    '.ogg':   'application/ogg',
    '.swf':   'application/x-shockwave-flash',
    '.tgz':   'application/x-gtar',
    '.wml':   'text/vnd.wap.wml',
    '.xul':   'application/vnd.mozilla.xul+xml',
    '.patch': 'text/plain'
    })


class IndexationFailure(Exception):
    """raised when an indexation has failed"""

class MetaConverter(type):
    """a simple metaclass for automatic converter registration"""
    def __new__(cls, classname, bases, classdict):
        klass = type.__new__(cls, classname, bases, classdict)
        mimetypes = classdict.get('MIME_TYPES', [])
        for mimetype in mimetypes:
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

    def extractWordsFromFile(self, filepath):
        """entry point of each converter class

        :returns: a word-vector
        """
        parser = self.getParser()
        try:
            return parser.parseFile(filepath, osp.basename(filepath),
                                    self.OUTPUT_ENCODING)
        except Exception, exc:
            raise IndexationFailure("Cannot parse document %s (because %s)" % (filepath, exc))
        


class RawTextConverter(BaseConverter):
    """provides simple text parser"""
    OUTPUT_TYPE = 'text'
    MIME_TYPES = ('text/plain', 'text/x-python', 'text/x-csrc', 'text/x-c++src',
                  'text/x-java')

    def getParser(self):
        return TextParser()
        
class HTMLConverter(BaseConverter):
    """provides a simple HTML parser"""
    OUTPUT_TYPE = 'html'
    MIME_TYPES = ('text/html',)

    def getParser(self):
        return HTMLParser() # This is really MaayHTMLParser from texttool

class ImageConverter(BaseConverter):
    """provides base Image converter
       In the future, it may hold EXIF information retrieval methods"""
    OUTPUT_TYPE = 'image'
    MIME_TYPES = ('image/jpeg','image/png', 'image/x-xpixmap')

    def getParser(self):
        return ExifParser()


def uncompressFile(filepath, outputDir):
    """returns a filepath for the same, uncompressed, file
       located in the provided output dir
    """
    if filepath.endswith('.gz'):
        opener = gzip.open
    elif filepath.endswith('.bz2'):
        opener = bz2.BZ2File
    else:
        opener = file
    compressed = opener(filepath, 'rb')
    uncompressedFile = osp.join(outputDir, osp.basename(filepath+"-in"))
    uncompressed = file(uncompressedFile, 'wb')
    uncompressed.write(compressed.read())
    compressed.close()
    uncompressed.close()
    return uncompressedFile
    

class CommandBasedConverter(BaseConverter):
    COMMAND = None

    def extractWordsFromFile(self, filepath):
        """XXX: some nasty side-effects lurking here
           1) for ps2ascii to work, we must have inputFile != outputFile
              hence the "-in" which is concatenated in uncompressFile above
           2) pdftohtml will always generate a wrongly titled document named
              after the input file (ie 'foo.pdf-in')
           For the title problem, we provide this workaround : provide
           the correct filename as additional parameter to the parser.
        """

        outputDir = mkdtemp()
        outputFile = osp.join(outputDir, osp.basename(filepath))
        inputFile = ''

        try:
            try:
                inputFile = uncompressFile (filepath, outputDir)
            except Exception, exc:
                raise IndexationFailure("Unable to index %r [%s]" % (filepath, exc))

            command_args = {'input' : inputFile, 'output' : outputFile}
            cmd = self.COMMAND % command_args

            #print "Executing %r" % cmd
            errcode = os.system(cmd)
            if errcode: # NOK
                raise IndexationFailure('Unable to index %r' % filepath)

            parser = self.getParser()
            try:
                return parser.parseFile(outputFile, osp.basename(filepath),
                                    self.OUTPUT_ENCODING)
            except Exception:
                raise IndexationFailure('Unable to index %r' % filepath)
                
        finally:
            try:
                if osp.isfile(outputFile):
                    os.remove(outputFile)
                if osp.isfile(inputFile):
                    os.remove(inputFile)
                os.rmdir(outputDir)
            except OSError:
                print "leaving %s behind" % outputDir


class PDFConverter(CommandBasedConverter, HTMLConverter):
    """This PDF converter has a little problem :
       it uses pdftohtml which systematically builds a html
       file whose TITLE field is its input file name.
       This can inpact the title guessing algorithm we want.
    """
    COMMAND = 'pdftohtml -i -q -noframes -stdout -enc UTF-8 "%(input)s" > "%(output)s"'
    OUTPUT_TYPE = 'html'
    MIME_TYPES = ('application/pdf',)
    OUTPUT_ENCODING = 'UTF-8'

class PSConverter(CommandBasedConverter, RawTextConverter):
    COMMAND = 'ps2ascii "%(input)s" "%(output)s"'
    MIME_TYPES = ('application/postscript',)

class RTFConverter(CommandBasedConverter, RawTextConverter):
    COMMAND = 'unrtf --html "%(input)s" > "%(output)s"'
    OUTPUT_TYPE = 'html'
    MIME_TYPES = ('text/rtf',)

class MSWordConverter(CommandBasedConverter, RawTextConverter):
    COMMAND = 'antiword "%(input)s" > "%(output)s"'
    MIME_TYPES = ('application/msword',)

def extractWordsFromFile(filename):
    mimetype = guess_type(filename)[0]
    converters = REGISTRY.get(mimetype, [])
    for klass in converters:
        try:
            converter = klass()
            return converter.extractWordsFromFile(filename)
        except IndexationFailure:
            print "indexation failed for %s, trying another converter" % filename
            continue
    # reaching this point means that none of our converters was able
    # to decode the input file
    raise IndexationFailure("Could not index file %r" % filename)

def isKnownType(filename):
    mimetype = guess_type(filename)[0]
    return mimetype in REGISTRY
