# -*- encoding: iso-8859-1 -*-
"""querier test cases"""

import unittest
from mimetypes import guess_type

from maay.dbentity import *

class Document_TC(unittest.TestCase):
    def testContainingQuery(self):
        query, params = Document._selectContainingQuery(['un', u'été', u'à', 'la', 'mer'],
                                                        allowPrivate=True)
        self.assertEquals(params, [u'un', u'ete', u'la', u'mer', 4])
        for p in params[:-1]:
            self.assertEquals(type(p), unicode)
        self.assertEquals(len(params), params[-1] + 1)
        expected = "SELECT D.db_document_id, D.document_id, D.title, D.size, D.text, D.url, D.mime_type, D.publication_time FROM documents D, document_scores DS WHERE DS.db_document_id=D.db_document_id AND DS.word IN (%s, %s, %s, %s) GROUP BY DS.db_document_id HAVING count(DS.db_document_id) = %s LIMIT 15 OFFSET 0"
        self.assertEquals(query.split(), expected.split())
        q = query%tuple(params) # sanity check for argument count
        
    def testContainingQueryWithOffset(self):
        query, params = Document._selectContainingQuery(['un', u'été', u'à', 'la', 'mer'],
                                                        offset=15, allowPrivate=True)
        self.assertEquals(params, [u'un', u'ete', u'la', u'mer', 4])
        for p in params[:-1]:
            self.assertEquals(type(p), unicode)
        self.assertEquals(len(params), params[-1] + 1)
        expected = "SELECT D.db_document_id, D.document_id, D.title, D.size, D.text, D.url, D.mime_type, D.publication_time FROM documents D, document_scores DS WHERE DS.db_document_id=D.db_document_id AND DS.word IN (%s, %s, %s, %s) GROUP BY DS.db_document_id HAVING count(DS.db_document_id) = %s LIMIT 15 OFFSET 15"
        self.assertEquals(query.split(), expected.split())
        q = query%tuple(params) # sanity check for argument count
        

    def testContainingQueryWithOffsetOnlyPublic(self):
        query, params = Document._selectContainingQuery(['un', u'été', u'à', 'la', 'mer'],
                                                        offset=15)
        self.assertEquals(params, [u'un', u'ete', u'la', u'mer', Document.PUBLISHED_STATE, 4])
        for p in params[:-2]:
            self.assertEquals(type(p), unicode)
        self.assertEquals(len(params), params[-1] + 2)
        expected = "SELECT D.db_document_id, D.document_id, D.title, D.size, D.text, D.url, D.mime_type, D.publication_time FROM documents D, document_scores DS WHERE DS.db_document_id=D.db_document_id AND DS.word IN (%s, %s, %s, %s) AND D.state=%s GROUP BY DS.db_document_id HAVING count(DS.db_document_id) = %s LIMIT 15 OFFSET 15"
        self.assertEquals(query.split(), expected.split())
        q = query%tuple(params) # sanity check for argument count
        
    

    def testContainingQueryWithMimetype(self):
        query, params = Document._selectContainingQuery(['un', u'été', u'à', 'la', 'mer'],
                                                        mimetype='text/plain',
                                                        allowPrivate=True)
        self.assertEquals(params, [u'un', u'ete', u'la', u'mer', 'text/plain', 4])
        for p in params[:-1]:
            self.assertEquals(type(p), unicode)
        self.assertEquals(len(params), params[-1] + 2)
        expected = "SELECT D.db_document_id, D.document_id, D.title, D.size, D.text, D.url, D.mime_type, D.publication_time FROM documents D, document_scores DS WHERE DS.db_document_id=D.db_document_id AND DS.word IN (%s, %s, %s, %s)   AND D.mime_type=%s  GROUP BY DS.db_document_id HAVING count(DS.db_document_id) = %s LIMIT 15 OFFSET 0"
        self.assertEquals(query.split(), expected.split())
        q = query%tuple(params) # sanity check for argument count
        
    

class NodeInterest_TC(unittest.TestCase):
    def setUp(self):
        self.entity = NodeInterest(node_id="0"*40, word="espadon",
                                   claim_count=0.5, specialisation=.25,
                                   expertise=.75)

    def tearDown(self):
        pass

    def testInsertQuery(self):
        """tests basic INSERT query generation"""
        query = self.entity._insertQuery()
        self.assertEquals(query,
                          "INSERT INTO node_interests (node_id, word, "
                          "claim_count, specialisation, expertise) "
                          "VALUES (%(node_id)s, %(word)s, %(claim_count)s, "
                          "%(specialisation)s, %(expertise)s)")

    def testIncompleteInsertQuery(self):
        """tests INSERT query generation when only some of the instance's
        attributes are set
        """
        entity = Word(word='foo', claim_count=2)
        query = entity._insertQuery()
        self.assertEquals(query,
                          "INSERT INTO words (word, claim_count) "
                          "VALUES (%(word)s, %(claim_count)s)")
        
    def testUpdateQuery(self):
        """tests UPDATE query generation"""
        query = self.entity._updateQuery()
        self.assertEquals(query,
                          "UPDATE node_interests SET node_id=%(node_id)s, word=%(word)s, "
                          "claim_count=%(claim_count)s, "
                          "specialisation=%(specialisation)s, expertise=%(expertise)s "
                          "WHERE node_id=%(node_id)s AND word=%(word)s")

    def testIncompleteUpdateQuery(self):
        """tests UPDATE query generation when only some of the instance's
        attributes are set
        """
        entity = Word(word='foo', claim_count=2)
        query = entity._updateQuery()
        self.assertEquals(query,
                          "UPDATE words SET word=%(word)s, claim_count=%(claim_count)s "
                          "WHERE word=%(word)s")

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
