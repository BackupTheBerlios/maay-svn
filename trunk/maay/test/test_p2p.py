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

"""unit tests for P2P queries"""

__revision__ = '$Id$'

import unittest
from maay.query import Query
from maay.p2pquerier import *
from maay.dbentity import Document

class P2pQueryTC(unittest.TestCase):
    def setUp(self):
        self.query = P2pQuery(sender='http://localhost:3423', # should be a hash (auc)
                              port=3423,
                              query=Query.fromRawQuery("foo"),
                              qid=42)

    def testHop(self):
        ttl = self.query.ttl
        self.query.hop()
        self.assertEquals(self.query.ttl, ttl-1)

    def testAddMatch(self):
        doc = Document(document_id = '0'*40)
        self.query.addMatch(doc.__dict__)
        self.failUnless('0'*40 in self.query.documents_ids)

    def testIsKnown(self):
        doc = Document(document_id = '0'*40)
        self.query.addMatch(doc.__dict__)
        self.failUnless(self.query.isKnown(doc.__dict__))
        self.failIf(self.query.isKnown(Document(document_id = '1'*40).__dict__))

    def testSimpleQueryAsKwargs(self):
        self.assertEquals(self.query.asKwargs(),
                          {'qid' : 42,
                           'sender' : 'http://localhost:3423',
                           'port' : 3423,
                           'ttl' : 5, # default value
                           'words' : [u'foo'],
                           'version' : 1,
                           'mime_type' : ''})

    def testComplexQueryAsKwargs(self):
        query = P2pQuery(sender='http://localhost:3423',
                         port = 3423,
                         ttl=2,
                         query=Query.fromRawQuery("foo bar filetype:pdf"),
                         qid=42)
        self.assertEquals(query.asKwargs(),
                          {'qid' : 42,
                           'sender' : 'http://localhost:3423',
                           'port' : 3423,
                           'ttl' : 2,
                           'words' : [u'foo', u'bar'],
                           'version' : 1,
                           'mime_type' : 'application/pdf'})
        
    

class P2pQuerierTC(unittest.TestCase):
    def setUp(self):
        self.querier = P2pQuerier('0'*40, None) 
        self.query = P2pQuery(sender='http://localhost:3423',
                              port=3423,
                              ttl=2,
                              query=Query.fromRawQuery("foo"))

    def tearDown(self):
        self.querier._queries = {}

    def test_selectTargetNeighbors(self):
        pass
        
if __name__ == '__main__':
    unittest.main()
