import unittest

from maay.server import Query

class UtilsTC(unittest.TestCase):

    def testBasicQuery(self):
        query = Query.fromRawQuery(u"hello")
        self.assertEquals(query.words, u"hello")
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, None)
        self.assertEquals(query.offset, 0)
        
    def testBasicQueryWithSeveralWords(self):
        query = Query.fromRawQuery(u"hello world")
        self.assertEquals(query.words, u"hello world")
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, None)
        self.assertEquals(query.offset, 0)
        
    def testOneWordRestrictedQuery(self):
        query = Query.fromRawQuery(u"hello filetype:pdf")
        self.assertEquals(query.words, u"hello")
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, 'application/pdf')
        self.assertEquals(query.offset, 0)

    def testTwoWordsRestrictedQuery(self):
        query = Query.fromRawQuery(u"hello filetype:pdf world")
        self.assertEquals(query.words, u"hello world")
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, 'application/pdf')
        self.assertEquals(query.offset, 0)

    def testTwoWordsRestrictedQueryAndOffset(self):
        query = Query.fromRawQuery(u"hello filetype:pdf world", 12)
        self.assertEquals(query.words, u"hello world")
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, 'application/pdf')
        self.assertEquals(query.offset, 12)

    # Commented because not sure how filename should be handled  :
    # (regexps ? LIKE %...% ?, etc.)
##     def testSeveralWordsAndSeveralRestrictions(self):
##         query = Query.fromRawQuery(u"hello filetype:pdf world filename:foo")
##         self.assertEquals(query.words, u"hello world")
##         self.assertEquals(query.filename, u"foo")
##         self.assertEquals(query.filetype, 'text/pdf')


if __name__ == '__main__':
    unittest.main()


