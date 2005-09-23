# -*- coding: iso-8859-1 -*-
"querier test cases"""

import unittest
import sha

from logilab.common.testlib import MockConnection
from logilab.common.db import get_connection
from maay.querier import MaayQuerier, normalizeText, Document, FileInfo



class QuerierTC(unittest.TestCase):
    def setUp(self):
        self.cnx = get_connection(driver='mysql', host='crater',
                                  database='maay_test', user='adim',
                                  password='adim')
        self.querier = MaayQuerier(connection=self.cnx)

    def tearDown(self):
        cursor = self.cnx.cursor()
        for table in ('document_providers', 'document_scores', 'documents',
                      'files', 'node_interests', 'nodes', 'words'):
            cursor.execute('DELETE FROM %s' % table)
        cursor.close()
        self.cnx.close()

        
    def test_execute(self):
        answ = self.querier._execute('SELECT * from documents')
        self.assertEquals(list(answ), [])

    def testIndexDocument(self):
        text = u"""Le tartuffe, de Jean-Baptiste Poquelin, dit Molière.

Le petit chat est mort."""
        text = normalizeText(text)
        digest = sha.sha(text).hexdigest()
        cursor = self.cnx.cursor()
        # At this point, database should be emtpy, so no document
        # should match <digest>
        matchingDocs = Document.selectWhere(cursor, document_id=digest)
        self.assertEquals(len(matchingDocs), 0)
        self.querier.indexDocument('/tmp/Tartuffe.txt',
                                   'Le Tartuffe',
                                   text,
                                   len(text),
                                   30000,
                                   digest,
                                   'text',
                                   Document.PUBLISHED_STATE,
                                   FileInfo.CREATED_FILE_STATE)
        matchingDocs = Document.selectWhere(cursor, document_id=digest)
        self.assertEquals(len(matchingDocs), 1)
        self.assertEquals(matchingDocs[0].text, text)
        

    def test_normalizeText(self):
        self.assertEquals(normalizeText(u"ÉtùïÄç"), "etuiac")


if __name__ == '__main__':
    unittest.main()
