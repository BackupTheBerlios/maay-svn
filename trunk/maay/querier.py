"""provides the MaayQuerier class"""

__revision__ = '$Id$'
__metaclass__ = type

from mimetypes import guess_type
import re
import time

import MySQLdb

from maay.dbentity import *


WORD_MIN_LEN = 2
WORD_MAX_LEN = 50

MAX_STORED_SIZE = 65535

WORDS_RGX = re.compile(r'\w{%s,%s}' % (WORD_MIN_LEN, WORD_MAX_LEN)) # XXX: need to handle diacritics signs

class MaayQuerier:
    """High-Level interface to Maay SQL database"""
    def __init__(self, host='', database='', user='', password=''):
        self._cnx = MySQLdb.connect(host=host, db=database,
                                    user=user, passwd=password)

    def _execute(self, query, args=None):
        cursor = self._cnx.cursor()
        results = []
        try:
            cursor.execute(query, args)
            results = cursor.fetchall()
        except:
            print "GOT ERROR while executing %r/%s ... rollback" % (query, args)
            self._cnx.rollback()
        else:
            cursor.close()
            self._cnx.commit()
        return results
        
    def findDocuments(self, words):
        if not words:
            return []
        columns = ['document_id', 'title', 'size', 'text', 'url', 'mime_type']
        args = {'words' : '(' + ','.join([repr(word) for word in words]) + ')',
                'lenwords' : len(words)}
        # XXX: what is the HAVING clause supposed to do ?
        query = """SELECT %s
                    FROM documents D, document_scores DS 
                    WHERE DS.db_document_id=D.db_document_id AND DS.word IN %%(words)s
                    GROUP BY DS.db_document_id
                    HAVING count(DS.db_document_id) = %%(lenwords)s""" % (
            ['D.%s' % col for col in columns])
        # for each row, build a dict from list of couples (attrname, value)
        # and build a DBEntity from this dict
        results = [Document(**dict(zip(columns, row))) for row in self._execute(query, args)]
        return results


    def getFilesInformations(self, **args):
        cursor = self._cnx.cursor()
        results = FileInfo.selectWhere(cursor, filename=file_name)
        cursor.close()
        return results

    def insertDocument(self, docId, filename, title, text, links, offset, fileSize, lastModTime, nodeID):
        mimetype = guess_type(filename)[0]
        doc = self.insertDocumentInfo(docId, title, mimetype, text, fileSize,
                                      lastModTime, filename)
        scores = self.getScoresForDocument(doc, text, links, offset)
        cursor = self._cnx.cursor()
        dbDocumentScores = {}
        for documentScore in DocumentScore.buildElementsFromTable(cursor):
            dbDocumentScores[documentScore.word] = documentScore
        for word, position in scores.iteritems():
            try:
                dbDocumentScore = dbDocumentScores[word]
            except KeyError:
                update = False
                download_count = 0
            else:
                update = True
                download_count += dbDocumentScore.download_count
            documentScore = DocumentScore(doc.db_document_id, word, position,
                                          download_count, 0, 0)
            documentScore.commit(cursor, update)
        fileInfo = FileInfo(filename, lastModTime, doc.db_document_id,
                            Document.PUBLISHED_STATE,
                            FileInfo.CREATED_FILE_STATE)
        fileInfo.commit(cursor, update=False)
        provider = DocumentProvider(doc.db_document_id, nodeID, int(time.time()))
        provider.commit(cursor, update=False)

    def updateDocument(self, docId, filename, title, text, links, offset, fileSize, lastModTime, nodeID):
        pass ## FIXME this is where adim and alf stopped porting the code
    
    def insertDocumentInfo(self, docId, title, mimetype, text, size, publicationTime, url):
        downloadCount = 0 # XXX 
        # check if it exists first :
        title = MySQLdb.escape_string(title)
        text = MySQLdb.escape_string(text[:MAX_STORED_SIZE])
        url = MySQLdb.escape_string(url or "")
        query = """INSERT INTO documents (document_id, mime_type, title, size, text, publication_time, state, download_count, url, indexed) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')
                """ %  (docId, mimetype, title, size, text,
                        publicationTime, Document.UNKNOWN_STATE, downloadCount, url, 1)
        self._execute(query)
        return self.getDocumentWithId(docId)

    def getScoresForDocument(self, document, text, links, offset):
        """parse words from document's text and update DB infos"""
        scores = {}
        for match in WORDS_RGX.finditer(text):
            word = match.group(0)
            word = word.lower()
            position = match.start() - offset
            if position < 0:
                position = -1
            scores[word] = position
        return scores
                
    def getDocumentWithId(self, docId):
        """searchs the DB for a document with id <docId> and builds a Document
        instance with the results

        :return: `Document` or None if no document matches docId
        """
        columns = ['db_document_id', 'document_id', 'mime_type', 'title', 'size',
                   'text', 'publication_time', 'state', 'download_count', 'url']
        query = 'SELECT %s FROM documents WHERE document_id=%%(docId)s' % (
            ', '.join(columns))
        results = self._execute(query, {'docId' : docId})
        if results:
            # build a dict from list of couples (attrname, value) from the
            # first row and build a DBEntity from this dict
            return Document(**dict(zip(columns, results[0])))
        else:
            return None
