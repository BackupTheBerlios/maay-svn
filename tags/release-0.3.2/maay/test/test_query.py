#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify it
#     under the terms of the GNU General Public License as published by the
#     Free Software Foundation; either version 2 of the License, or (at your
#     option) any later version.
#     
#     This program is distributed in the hope that it will be useful, but
#     WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
#     Public License for more details.
#     
#     You should have received a copy of the GNU General Public License along
#     with this program; if not, write to the Free Software Foundation, Inc.,
#     59 Temple Place - Suite 330, Boston, MA 02111-1307 USA.
#     

__revision__ = '$Id$'

import unittest

from maay.query import Query

class QueryTC(unittest.TestCase):

    def testBasicQuery(self):
        query = Query.fromRawQuery(u"hello")
        self.assertEquals(query.words, [u"hello"])
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), list)
        self.assertEquals(type(query.words[0]), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, None)
        self.assertEquals(query.offset, 0)
        
    def testBasicQueryWithSeveralWords(self):
        query = Query.fromRawQuery(u"hello world")
        self.assertEquals(query.words, [u"hello",u"world"])
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), list)
        self.assertEquals(type(query.words[0]), unicode)
        self.assertEquals(type(query.words[1]), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, None)
        self.assertEquals(query.offset, 0)
        
    def testOneWordRestrictedQuery(self):
        query = Query.fromRawQuery(u"hello filetype:pdf")
        self.assertEquals(query.words, [u"hello"])
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), list)
        self.assertEquals(type(query.words[0]), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, 'application/pdf')
        self.assertEquals(query.offset, 0)

    def testTwoWordsRestrictedQuery(self):
        query = Query.fromRawQuery(u"hello filetype:pdf world")
        self.assertEquals(query.words, [u"hello", u"world"])
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), list)
        self.assertEquals(type(query.words[0]), unicode)
        self.assertEquals(type(query.words[1]), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, 'application/pdf')
        self.assertEquals(query.offset, 0)

    def testTwoWordsRestrictedQueryAndOffset(self):
        query = Query.fromRawQuery(u"hello filetype:pdf world", 12)
        self.assertEquals(query.words, [u"hello", u"world"])
        # excplitly check for unicode-ness ('hello' == u'hello')
        self.assertEquals(type(query.words), list)
        self.assertEquals(type(query.words[0]), unicode)
        self.assertEquals(type(query.words[1]), unicode)
        self.assertEquals(query.filename, None)
        self.assertEquals(query.filetype, 'application/pdf')
        self.assertEquals(query.offset, 12)

    def testMimeTypeNormalization(self):
        query = Query.fromRawQuery(u"hello filetype:pdf world", 12)
        self.assertEquals(query.filetype, 'application/pdf')
        query.filetype = 'text/x-python'
        self.assertEquals(query.filetype, 'text/x-python')
        query.filetype = ''
        self.assertEquals(query.filetype, None)
        query.filetype = 'pdf'
        self.assertEquals(query.filetype, 'application/pdf')
        query.filetype = None
        self.assertEquals(query.filetype, None)
        
    # Commented because not sure how filename should be handled  :
    # (regexps ? LIKE %...% ?, etc.)
##     def testSeveralWordsAndSeveralRestrictions(self):
##         query = Query.fromRawQuery(u"hello filetype:pdf world filename:foo")
##         self.assertEquals(query.words, u"hello world")
##         self.assertEquals(query.filename, u"foo")
##         self.assertEquals(query.filetype, 'text/pdf')


if __name__ == '__main__':
    unittest.main()


