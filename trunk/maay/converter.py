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

# XXX: need to handle file encodings

import os
from mimetypes import guess_type
from tempfile import mkdtemp

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
    # None means "let the text parser guess the encoding"
    OUTPUT_ENCODING = None

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
        return parser.parseFile(filename, self.OUTPUT_ENCODING)


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
        outputDir = mkdtemp()
        outputFile = os.path.join(outputDir, 'out.txt')
        command_args = {'input' : filename, 'output' : outputFile}
        cmd = self.COMMAND % command_args
        print "Executing %r" % cmd
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
            os.rmdir(outputDir)


class PDFConverter(CommandBasedConverter):
    # XXX: we could generate HTML (and thus obtain a real document
    #      title) with pdftotext or pdftohtml but :
    #        - pdftotex only wraps text between <pre> and </pre> tags
    #          and **doesn't escape** text. So if you have something
    #          like "<name>" in your document, you'll end up with
    #          a malformed HTML file
    #        - pdftohtml handles text correctly **but** doesn't provide
    #          any way to save the output elsewhere than in the current
    #          working directory
    #     So, for now, just use pdftotext without -htmlmeta option.
    #     Possible ways to circumvent the problem :
    #      1/ add a "stdout" OUTPUT_TYPE, and when OUTPUT_TYPE is set
    #        to "stdout", use popen() rather than os.system()
    #      2/ override extractWordsFromFile() for PDFConverter, but
    #         this will mainly be duplicated code
    #      3/ add pre/post parse hooks (and maybe pre/post exec hooks)
    #         to have a finer control on CommandBasesConverters
    #      ... and probably lot of other solutions

    # COMMAND = "pdftohtml -i -noframes -enc Latin1 %(input)s %(output)s"
    # COMMAND = "pdftotext -htmlmeta -enc Latin1 %(input)s %(output)s"
    COMMAND = "pdftotext -enc Latin1 %(input)s %(output)s"
    OUTPUT_TYPE = 'text'
    MIME_TYPE = 'application/pdf'
    OUTPUT_ENCODING = 'ISO-8859-1'

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
