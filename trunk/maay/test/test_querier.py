# -*- coding: iso-8859-1 -*-
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

"querier test cases"""

__revision__ = ''

import unittest
import sha

from logilab.common.testlib import MockConnection
from logilab.common.db import get_connection
from maay.querier import MaayQuerier, normalizeText, Document, FileInfo
from maay.dbentity import FutureDocument

class QuerierTC(unittest.TestCase):
    def setUp(self):
        self.cnx = get_connection(driver='mysql', host='localhost',
                                  database='maay_test', user='maay',
                                  password='maay')
        self.querier = MaayQuerier(connection=self.cnx)
        self.nodeId = '0'*40
        self.querier.registerNode(self.nodeId, "127.0.0.1", 6789, 10)

    def tearDown(self):
        cursor = self.cnx.cursor()
        for table in ('document_providers', 'document_scores', 'documents',
                      'files', 'node_interests', 'nodes', 'words'):
            cursor.execute('DELETE FROM %s' % table)
        cursor.close()
        self.querier.close()

        
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
        title = 'Le Tartuffe'
        matchingDocs = Document.selectWhere(cursor, document_id=digest)
        self.assertEquals(len(matchingDocs), 0)
        self.querier.indexDocument('0'*40, FutureDocument(
            filename='/tmp/Tartuffe.txt',
            title=title,
            text=text,
            fileSize=len(text),
            lastModificationTime=30000,
            content_hash=digest,
            mime_type='text',
            state=Document.PUBLISHED_STATE,
            file_state=FileInfo.CREATED_FILE_STATE))
        matchingDocs = Document.selectWhere(cursor, document_id=digest)
        self.assertEquals(len(matchingDocs), 1)
        self.assertEquals(matchingDocs[0].text, '%s %s' % (title, text))
        

    def test_normalizeText(self):
        self.assertEquals(normalizeText(u"ÉtùïÄç"), "etuiac")
        
if __name__ == '__main__':
    unittest.main()
