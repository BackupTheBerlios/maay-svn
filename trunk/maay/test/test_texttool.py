"""unit tests for Text and HTML parsers"""

import unittest

from maay.texttool import MaayHTMLParser

ROW_TEXT = "foo bar baz top bim bam boum"

SIMPLE_HTML = """<html>
<head><title>maille Maay</title></head>
<body>Hello world
This is <a href="something.com">a link</a>
and this is <a href="somethingelse.com">another link</a>
</body>
</html>
"""

class HTMLParserTC(unittest.TestCase):

    def setUp(self):
        self.parser = MaayHTMLParser()

    def testParseRaw(self):
        html = '<body>%s</body>' % ROW_TEXT
        title, text, links, offset = self.parser.parseString(html)
        self.assertEquals(title, '')
        self.assertEquals(text, ROW_TEXT)
        self.assertEquals(links, [])

    def testParseSimpleHtml(self):
        title, text, links, offset = self.parser.parseString(SIMPLE_HTML)
        self.assertEquals(title, 'maille Maay')
        self.assertEquals(text, 'hello world this is a link and this is another link')
        self.assertEquals(links, ['something.com', 'somethingelse.com'])
    

if __name__ == '__main__':
    unittest.main()
