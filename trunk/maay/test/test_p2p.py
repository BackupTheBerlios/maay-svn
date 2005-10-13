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

"""unit tests for P2P queries"""

__revision__ = '$Id$'

import unittest
from maay.server import Query
from maay.p2pquerier import *
from maay.dbentity import Document

class P2pQueryTC(unittest.TestCase):
    def setUp(self):
        self.query = P2pQuery(queryId='1'*40,
                              sender='http://localhost:3423',
                              ttl=2,
                              query=None)

    def testHop(self):
        ttl = self.query.ttl
        self.query.hop()
        self.assertEquals(self.query.ttl, ttl-1)

    def testAddMatch(self):
        doc = Document(document_id = '0'*40)
        self.query.addMatch(doc)
        self.failUnless('0'*40 in self.query.documents)

    def testIsKnown(self):
        doc = Document(document_id = '0'*40)
        self.query.addMatch(doc)
        self.failUnless(self.query.isKnown(doc))
        self.failIf(self.query.isKnown(Document(document_id = '1'*40)))

class P2pQuerierTC(unittest.TestCase):
    def setUp(self):
        self.querier = P2pQuerier('0'*40)
        self.query = P2pQuery(queryId='1'*40,
                              sender='http://localhost:3423',
                              ttl=2,
                              query=None)

    def tearDown(self):
        self.querier._queries = {}

    def test_selectTargetNeighbors(self):
        pass
        
if __name__ == '__main__':
    unittest.main()
