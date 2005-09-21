"""this module provide text / parsing tools"""

__revision__ = '$Id$'

from HTMLParser import HTMLParser
        
class TextParser:
    def parseFile(self, filename):
        """returns a 4-uple (title, normalized_text, links, offset)
        
        Aglorithm taken from original texttotext implementation
        """
        content = file(filename).read()
        return self.parseString(content)

    def parseString(self, source):
        result = normalize_text(source)
        title = result[:60]
        return title, result, [], 0
        

class MaayHTMLParser(HTMLParser):
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
    
    def parseFile(self, filename):
        """returns a 4-uple (title, normalized_text, links, offset)
        TODO: port original code from htmltotext
        """
        # XXX: really dummy implementation !!
        source = file(filename).read()
        return self.parseString(source)

    def parseString(self, source):
        self.feed(source)
        result = normalize_text(''.join(self.textbuf))
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
del maketrans

def normalize_text(text, table=_table):
    """turns everything to lowercase, and converts accentuated
    characters to non accentuated chars."""
    text = text.lower().translate(table)
    return ' '.join(text.split())

del _table
