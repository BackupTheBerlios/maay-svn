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

"""provides the MaayQuerier class"""

from __future__ import division

__revision__ = '$Id$'
__metaclass__ = type

from mimetypes import guess_type
import re
import time
from math import sqrt, log

from zope.interface import Interface, implements

from logilab.common.db import get_dbapi_compliant_module

from maay.dbentity import FutureDocument, Document, FileInfo, \
     DocumentProvider, DocumentScore, Word, Node
from maay.texttool import normalizeText, WORDS_RGX, MAX_STORED_SIZE

class MaayAuthenticationError(Exception):
    """raised on db authentication failure"""

ANONYMOUS_AVATARID = '__anonymous__'
WEB_AVATARID = '__may__'
    
class IQuerier(Interface):
    """defines the High-Level interface to Maay SQL database"""

    def findDocuments(query):
        """returns all Documents matching <query>"""

    def getFileInformations(filename):
        """returns a list of FileInfo's instances according
        to DB's content
        """

    def getIndexedFiles():
        """returns a list of indexed file names as strings
        """

    def indexDocument(nodeId, futureDoc):
        """Inserts or update information in table documents,
        file_info, document_score and word"""

    def removeFileInfo(filename):
        """remove filename from the database `files` table"""

    def removeUnreferencedDocuments():
        """remove rows in `documents` table when no row in `files` or
        `document_providers` table reference them, as well as the
        corresponding `document_scores` rows"""
        
    def notifyDownload(docId, query):
        """check that a document is downloadable and update the
        download statistics for the document.

        Return document url if the document is downloadable and and
        empty string otherwise"""
        
    def registerNode(nodeId, ip, port, bandwidth, lastSeenTime=None):
        """register a node in the database"""
        
    def registerNodeActivity(nodeId):
        """update lastSeenTime for node"""
        
    def close():
        """closes the DB connection"""


class AnonymousQuerier:
    """High-Level interface to Maay SQL database for anonymous
    (typically peers) users
    """
    implements(IQuerier)

    searchInPrivate = False
    
    def __init__(self, host='', database='', user='', password='',
                 connection=None):
        if connection is None:
            dbapiMod = get_dbapi_compliant_module('mysql')
            try:
                connection = dbapiMod.connect(host=host, database=database,
                                              user=user, password=password,
                                              unicode=True)
                # FIXME: find a better way to perform this operation
                # the autodetection of the charset guesses latin-1 and
                # this obviously does not work with unicode
                connection.charset = 'utf-8'
            except dbapiMod.OperationalError:
                raise MaayAuthenticationError("Failed to authenticate user %r"
                                              % user)
            except Exception, e:
                import traceback
                traceback.print_exc()
                raise MaayAuthenticationError(
                    "Failed to authenticate user %r [%s]" % (user, e))
        self._cnx = connection

    def _execute(self, query, args=None):
        cursor = self._cnx.cursor()
        results = []
        try:
            cursor.execute(query, args)
            results = cursor.fetchall()
        except:
            import traceback
            traceback.print_exc()
            print "GOT ERROR while executing %r/%s ... rollback" % (query, args)
            cursor.close()
            self._cnx.rollback()
        else:
            cursor.close()
            self._cnx.commit()
        return results

    def close(self):
        self._cnx.close()
        self._cnx = None

    def __del__(self):
        print "Querier", self, "is being GCed ... "
        if self._cnx:
            print " connection stats :", self._cnx.stat()
            self.close()

    def findDocuments(self, query):
        """Find all indexed documents matching the query"""
        # TODO: order results using document_scores information
        words = WORDS_RGX.findall(normalizeText(unicode(query.words)))
        self._updateQueryStatistics(words)
        try:
            cursor = self._cnx.cursor()
            return Document.selectContaining(cursor, words, query.filetype,
                                             query.offset, self.searchInPrivate)
        finally:
            cursor.close()

    def _updateScores(self, cursor, db_document_id, text):
        # insert or update in table document_score
        db_scores = self._getScoresDict(cursor, db_document_id)
        doc_scores = {}
        # We update the document_score table only for the first
        # occurence of the word in the document
        for match in WORDS_RGX.finditer(normalizeText(text)):
            word = match.group(0)
            if word in doc_scores:
                continue
            doc_scores[word] = 0
            position = match.start()
            if word in db_scores :
                if db_scores[word].position != position:
                    db_scores[word].position = position
                    db_scores[word].commit(cursor, update=True)
            else:
                # insert a row in the Word table if required
                self._ensureWordInDatabase(cursor, word)
                db_score = DocumentScore(db_document_id=db_document_id,
                                         word=word,
                                         position=position,
                                         download_count=0.,
                                         relevance=0.,
                                         popularity=0.)
                db_score.commit(cursor, update = False)
                    

    def _ensureWordInDatabase(self, cursor, word):
        db_words = Word.selectWhere(cursor, word=word)
        if not db_words:
            db_word = Word(word=word,
                           claim_count=0.,
                           download_count=0.)
            db_word.commit(cursor, update=False)
        
    def _getScoresDict(self, cursor, db_document_id):
        _scores = DocumentScore.selectWhere(cursor,
                                            db_document_id=db_document_id)
        db_scores = {}
        while _scores:
            score = _scores.pop()
            db_scores[score.word] = score
        return db_scores


    def _updateQueryStatistics(self, words):
        # FIXME: update node_interests too, but we need the nodeId to do this
        cursor = self._cnx.cursor()
        for word in words:
            winfo = Word.selectOrInsertWhere(cursor, word=word)[0]
            winfo.claim_count += 1 / len(words)
            winfo.commit(cursor, update=True)
        cursor.close()
        self._cnx.commit()


    def notifyDownload(self, db_document_id, query):
        words = WORDS_RGX.findall(normalizeText(query))
        try:
            try:
                cursor = self._cnx.cursor()
                doc = Document.selectWhere(cursor, db_document_id=db_document_id)[0]
            finally:
                cursor.close()
            self._updateDownloadStatistics(doc, words)
            return doc.url
        except IndexError:
            return ''

    def _updateDownloadStatistics(self, document, words):
        cursor = self._cnx.cursor()
        document.download_count = max(0, document.download_count) + 1
        document.commit(cursor, update=True)
        db_document_id = document.db_document_id
        scores = {}
        wordInfo = {}
        for word in words:
            scores[word] = DocumentScore.selectOrInsertWhere(cursor,
                                      db_document_id=db_document_id,
                                      word=word)[0]
            wordInfo[word] = Word.selectOrInsertWhere(cursor,
                                                      word=word)[0]

        for winfo in wordInfo.itervalues():
            winfo.download_count += 1 / len(words)
            winfo.commit(cursor, update=True)

        for word,score in scores.iteritems():
            score.download_count = max(0, score.download_count) + 1 / len(words)
            winfo_downloads = wordInfo[word].download_count
            
            score.popularity = score.download_count / winfo_downloads
            score.popularity -= hoeffding_deviation(winfo_downloads)
            
            score.relevance = score.download_count / document.download_count
            score.relevance -= hoeffding_deviation(document.download_count)
            
            score.commit(cursor, update=True)
        cursor.close()
        self._cnx.commit()


    def registerNode(self, nodeId, ip, port, bandwidth, lastSeenTime=None):
        """this will be used as a callback in registrationclient/login"""
        print "AnonymousQuerier registerNode (callback) %s %s:%s" % \
                                                             (nodeId, ip, port)
        lastSeenTime = lastSeenTime or int(time.time())
        cursor = self._cnx.cursor()
        node = Node.selectOrInsertWhere(cursor, node_id=nodeId)[0]
        node.ip = ip
        node.port = port
        node.bandwidth = bandwidth
        node.last_seen_time = lastSeenTime
        node.commit(cursor, update=True)
        cursor.close()

    def registerNodeActivity(self, nodeId):
        cursor = self._cnx.cursor()
        node = Node.selectWhere(cursor, node_id=nodeId)[0]
        node.last_seen_time = int(time.time())
        node.commit(cursor, update=True)
        cursor.close()

    def getRegisteredNeighbors(self, nodeId, nbNodes):
        cursor = self._cnx.cursor() 
        nodes = Node.selectRegistered(cursor, nodeId, nbNodes) 
        cursor.close()
        return nodes

    def getActiveNeighbors(self, nodeId, nbNodes):
        cursor = self._cnx.cursor() 
        nodes = Node.selectActive(cursor, nodeId, nbNodes) 
        cursor.close()
        return nodes
    
class MaayQuerier(AnonymousQuerier):
    """High-Level interface to Maay SQL database.

    The Querier receives requests from other components to insert or
    read data in the SQL database and dutifully executes these
    requests"""
    
    implements(IQuerier)

    searchInPrivate = True

    def getFileInformations(self, filename):
        cursor = self._cnx.cursor()
        results = FileInfo.selectWhere(cursor, file_name=filename)
        cursor.close()
        return list(results)

    def getIndexedFiles(self):
        cursor = self._cnx.cursor()
        results = FileInfo.selectWhere(cursor)
        cursor.close()
        return  [f.file_name for f in results]    
        
    def removeFileInfo(self, filename):
        """remove filename from the database `files` table"""
        cursor = self._cnx.cursor()
        rows = cursor.execute('DELETE FROM files WHERE file_name = %s',
                              filename)
        cursor.close()
        self._cnx.commit()
        #print "removed %s" % filename
        return rows

    def removeUnreferencedDocuments(self):
        """remove rows in `documents` table when no row in `files` or
        `document_providers` table reference them, as well as the
        corresponding `document_scores` rows"""
        cursor = self._cnx.cursor()
        query1 = """DELETE documents
                    FROM documents LEFT JOIN files
                             ON documents.db_document_id = files.db_document_id
                    WHERE files.db_document_id IS NULL"""
        rows = cursor.execute(query1)
        query2 = """DELETE document_scores
                    FROM document_scores LEFT JOIN  documents
                       ON document_scores.db_document_id = documents.db_document_id
                    WHERE documents.db_document_id IS NULL"""
        rows += cursor.execute(query2)
        cursor.close()
        self._cnx.commit()
        print "removed %d rows related to unreferenced documents" % rows
        return rows

    def indexDocument(self, nodeId, futureDoc):
        """Inserts or update information in table documents,
        file_info, document_score and word"""
        # XXX Decide if we can compute the content_hash and mime_type
        # ourselves or if the indexer should do it and
        # pass the values as an argument
        cursor = self._cnx.cursor()
        # insert or update in table file_info
        fileinfo = FileInfo.selectWhere(cursor, file_name=futureDoc.filename)
        # insert title into text to be able to find documents according
        # to their title (e.g: searching 'foo' should find 'foo.pdf')
        futureDoc.text = '%s %s' % (futureDoc.title, futureDoc.text)
        if fileinfo:
            fileinfo = fileinfo[0]
            fileinfo.file_time = futureDoc.lastModificationTime
            fileinfo.state = futureDoc.state
            fileinfo.file_state = futureDoc.file_state
            doc = Document.selectWhere(cursor,
                                       db_document_id=fileinfo.db_document_id)
            if not doc or doc[0].document_id!=futureDoc.content_hash :
                # no document was found or a document with another content
                # in both case, we create a new Document in database
                # (we don't want to modify the existing one, because it
                # can be shared by several files)
                doc = self._createDocument(cursor, futureDoc)
                fileinfo.db_document_id = doc.db_document_id
            else:
                # document has not changed
                doc = doc[0]
                if doc.state != futureDoc.state:
                    doc.state = futureDoc.state
                    doc.commit(cursor, update=True)
                
            fileinfo.commit(cursor, update=True)
                
        else:
            # file unknown
            # try to find a Document with same hash value
            doc = Document.selectWhere(cursor,
                                       document_id=futureDoc.content_hash)
            if doc:
                doc = doc[0]
                doc.state = futureDoc.state
                doc.publication_time = max(doc.publication_time,
                                           futureDoc.lastModificationTime)
                doc.commit(cursor, update=True)
            else:
                doc = self._createDocument(cursor, futureDoc)
                doc = Document.selectWhere(cursor, document_id=futureDoc.content_hash)[0]

            fileinfo = FileInfo(db_document_id=doc.db_document_id,
                                file_name=futureDoc.filename,
                                file_time=futureDoc.lastModificationTime,
                                state=futureDoc.state,
                                file_state=futureDoc.file_state)
            fileinfo.commit(cursor, update=False)

        self._updateScores(cursor, doc.db_document_id, futureDoc.text)
        provider = DocumentProvider.selectOrInsertWhere(cursor,
                                          db_document_id=doc.db_document_id,
                                          node_id=nodeId)[0]
        provider.last_providing_time = int(time.time())
        provider.commit(cursor, update=True)
        node = Node.selectWhere(cursor, node_id=nodeId)[0]
        node.last_seen_time = int(time.time())
        node.commit(cursor, update=True)
        cursor.close()
        self._cnx.commit()
        
    def _createDocument(self, cursor, futureDoc):

        doc = Document(document_id=futureDoc.content_hash,
                       title=futureDoc.title,
                       text=futureDoc.text[:MAX_STORED_SIZE],
                       size=futureDoc.fileSize,
                       publication_time=futureDoc.lastModificationTime,
                       download_count=0.,
                       url=futureDoc.filename,
                       mime_type=futureDoc.mime_type,
                       matching=0.,
                       indexed='1',
                       state=futureDoc.state)
        doc.commit(cursor, update=False)
        doc = Document.selectWhere(cursor, document_id=futureDoc.content_hash)[0]
        return doc

def hoeffding_deviation(occurence, confidence=0.9):
     return sqrt(-log(confidence / 2) / (2 * occurence))
