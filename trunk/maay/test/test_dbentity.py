"""querier test cases"""

import unittest
from mimetypes import guess_type

from logilab.common.testlib import MockConnection

from maay.dbentity import *

class NodeInterest_TC(unittest.TestCase):
    def setUp(self):
        self.entity = NodeInterest(node_id="0"*40, word="espadon",claim_count=0.5,
                              specialisation=.25, expertise = .75)

    def tearDown(self):
        pass

    def testInsertQuery(self):
        query = self.entity._insertQuery()
        self.assertEquals(query,
                          "INSERT INTO node_interests (node_id, word, "
                          "claim_count, specialisation, expertise) "
                          "VALUES (%(node_id)s, %(word)s, %(claim_count)s, "
                          "%(specialisation)s, %(expertise)s)")
    def testUpdateQuery(self):
        query = self.entity._updateQuery()
        self.assertEquals(query,
                          "UPDATE node_interests SET node_id=%(node_id)s, word=%(word)s, "
                          "claim_count=%(claim_count)s, "
                          "specialisation=%(specialisation)s, expertise=%(expertise)s "
                          "WHERE node_id=%(node_id)s AND word=%(word)s")

    def testSelectQuery(self):
        query = NodeInterest._selectQuery()
        self.assertEquals(query,
                          "SELECT node_id, word, claim_count, specialisation, expertise FROM node_interests")
    def testSelectQueryWhere(self):
        query = NodeInterest._selectQuery(('word', 'node_id'))
        self.assertEquals(query,
                          "SELECT node_id, word, claim_count, specialisation, expertise FROM node_interests WHERE word=%(word)s AND node_id=%(node_id)s")

if __name__ == '__main__':
    unittest.main()
