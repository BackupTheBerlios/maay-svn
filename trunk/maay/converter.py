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

import os
from mimetypes import guess_type

from maay.texttool import TextParser, MaayHTMLParser as HTMLParser

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

    def getParser(self):
        if self.OUTPUT_TYPE == 'html':
            return HTMLParser()
        else:
            return TextParser()

    def extractWordsFromFile(self, filename):
        """entry point of each converter class

        :returns: a word-vector
        """
        parser = self.getParser()
        return parser.parseFile(filename)


class RawTextConverter(BaseConverter):
    """provides simple text parser"""
    OUTPUT_TYPE = 'text'
    MIME_TYPE = 'text/plain'
        
class HTMLConverter(BaseConverter):
    """provides a simple HTML parser"""
    OUTPUT_TYPE = 'html'
    MIME_TYPE = 'text/html'

class CommandBasedConverter(BaseConverter):
    COMMAND = None
    def extractWordsFromFile(self, filename):
        command_args = {'input' : filename, 'output' : '/tmp/out.txt'}
        cmd = self.COMMAND % command_args
        print "Executing %r" % cmd
        errcode = os.system(cmd)
        if errcode == 0: # OK
            parser = self.getParser()
            return parser.parseFile('/tmp/out.txt')
        else:
            raise IndexationFailure('Unable to index %r' % filename)


class PDFConverter(CommandBasedConverter):
    COMMAND = "pdftotext -htmlmeta %(input)s %(output)s"
    OUTPUT_TYPE = 'html'
    MIME_TYPE = 'application/pdf'

class PSConverter(CommandBasedConverter):
    COMMAND = "ps2ascii %(input)s %(output)s"
    MIME_TYPE = 'application/postscript'

class RTFConverter(CommandBasedConverter):
    COMMAND = "unrtf --html %(input)s > %(output)s"
    OUTPUT_TYPE = 'html'
    MIME_TYPE = 'text/rtf'

class MSWordConverter(CommandBasedConverter):
    COMMAND = "antiword %(input)s > %(output)s"
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
