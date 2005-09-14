"""this module handles Converter Registry

Typical use ::

    >>> from maay.converter import extractWordsFromFile
    >>> words = extractWordsFromFile('foo.pdf')
    >>> words = extractWordsFromFile('foo.doc')

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
import re
from mimetypes import guess_type

TAG = re.compile('<.*?>', re.S)
def remove_tags(htmlsource):
    return TAG.sub('', htmlsource)

# REGISTRY is a mimetype / converterList map
REGISTRY = {}

class IndexationFailure(Exception):
    """raised when an indexation has failed"""


class TextParser:
    def parseFile(self, filename):
        """returns a couple (title, normalized_text)
        Aglorithm taken from original texttotext implementation
        """
        content = file(filename).read()
        return self.parseString(content)

    def parseString(self, source):
        table = ''.join([' ' * 32] + [chr(i) for i in xrange(32, 256)])
        translated = content.translate(table)
        # normalize white spaces
        result = ' '.join(translated.split())
        title = result[:60]
        return title, result
        

class HTMLParser:
    def parseFile(self, filename):
        """returns a couple (title, normalized_text)
        TODO: port original code from htmltotext
        """
        # XXX: really dummy implementation !!
        source = file(filename).read()
        return TextParser().parseString(source)


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
    print "Could not index file %r" % filename
    return []
