# -*- coding: iso-8859-1 -*-
"querier test cases"""

import unittest
import sha

from logilab.common.testlib import MockConnection

from maay.querier import MaayQuerier, normalize_word, Document, FileInfo



class QuerierTC(unittest.TestCase):
    def setUp(self):
        self.cnx = MockConnection([])
        self.querier = MaayQuerier(connection = self.cnx)
    def tearDown(self):
        self.cnx.close()

    def test_execute(self):
        answ = self.querier._execute('SELECT * FROM titi')
        self.assertEquals(answ, [])

    def testIndexDocument(self):
        text = """Le tartuffe, de Jean-Baptiste Poquelin, dit Molière.

Le petit chat est mort."""
        
        self.querier.indexDocument('/tmp/Tartuffe.txt',
                                   'Le Tartuffe',
                                   text,
                                   len(text),
                                   30000,
                                   sha.sha(text).hexdigest(),
                                   'text',
                                   Document.PUBLISHED_STATE,
                                   FileInfo.CREATED_FILE_STATE)
                                   
                                   


    def test_normalize_word(self):
        self.assertEquals(normalize_word("ÉtùïÄç"), "etuiac")


if __name__ == '__main__':
    unittest.main()
