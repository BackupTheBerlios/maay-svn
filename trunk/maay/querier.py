# -*- coding: iso-8859-1 -*- 
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

"""provides the MaayQuerier class"""

from __future__ import division

__revision__ = '$Id$'
__metaclass__ = type

import time
from mx.DateTime import now, DateTimeDelta
import traceback
import base64
from math import sqrt, log as mathlog

from twisted.python import log
from zope.interface import Interface, implements

from logilab.common.db import get_dbapi_compliant_module

from maay.dbentity import ScoredDocument, Document, FileInfo, \
     DBEntity, DocumentProvider, DocumentScore, Word, Node, Result
from maay.texttool import normalizeText, WORDS_RGX, MAX_STORED_SIZE

IntegrityError = None


class MaayAuthenticationError(Exception):
    """raised on db authentication failure"""

ANONYMOUS_AVATARID = '__anonymous__'
WEB_AVATARID = '__may__'
ONE_HOUR = DateTimeDelta(0, 1)
    
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

    def getDocumentCount(self):
        """get document count"""

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
            global IntegrityError
            dbapiMod = get_dbapi_compliant_module('mysql')
            IntegrityError = dbapiMod.IntegrityError
            try:
                connection = dbapiMod.connect(host=host, database=database,
                                              user=user, password=password,
                                              unicode=True)
                # FIXME: find a better way to perform this operation
                # the autodetection of the charset guesses latin-1 and
                # this obviously does not work with unicode
                connection.charset = 'UTF-8'
            except dbapiMod.OperationalError:
                raise MaayAuthenticationError("Failed to authenticate user %r"
                                              % user)
            except Exception, e:
                traceback.print_exc()
                raise MaayAuthenticationError(
                    "Failed to authenticate user %r [%s]" % (user, e))
        self._cnx = connection
        self.flushTemporaryTable()
    
    def _execute(self, query, args=None):
        cursor = self._cnx.cursor()
        results = []
        try:
            cursor.execute(query, args)
            results = cursor.fetchall()
        except:
            traceback.print_exc()
            print "GOT ERROR while executing %r/%s ... rollback" % (query, args)
            cursor.close()
            self._cnx.rollback()
        else:
            cursor.close()
            self._cnx.commit()
        return results

    def flushTemporaryTable(self): #FIXME : this is really the results table
        self._execute('DELETE FROM results')
        
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
        words = query.words
        self._updateQueryStatistics(words)
        try:
            cursor = self._cnx.cursor()
            # FIXME: it's quite obvious that we should feed the whole query
            return ScoredDocument.selectContaining(cursor, words,
                                                   query.filetype,
                                                   query.offset,
                                                   query.limit,
                                                   self.searchInPrivate,
                                                   order=query.order,
                                                   direction=query.direction)
        finally:
            traceback.print_exc()
            cursor.close()
        return []
        
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

    def notifyDownload(self, document_id, words):
        #words = [WORDS_RGX.findall(normalizeText(unicode(word)))
        #         for word in words]
        print "Querier notifyDownloads %s with %s" % (document_id, words)
        try:
            try:
                cursor = self._cnx.cursor()
                doc = Document.selectWhere(cursor, document_id=document_id)[0]
            finally:
                cursor.close()
            self._updateDownloadStatistics(doc, words)
            return doc.pristineUrl()
        except IndexError:
            raise

    def _updateDownloadStatistics(self, document, words):
        cursor = self._cnx.cursor()
        document.download_count = max(0.0, document.download_count) + 1
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
            winfo.download_count += 1.0 / len(words)
            winfo.commit(cursor, update=True)

        for word,score in scores.iteritems():
            score.download_count = max(0.0, score.download_count) + 1.0 / len(words)
            winfo_downloads = wordInfo[word].download_count
            
            score.popularity = float(score.download_count) / winfo_downloads
            score.popularity -= hoeffding_deviation(winfo_downloads)
            score.popularity = max(1e-6, score.popularity)
            
            score.relevance = float(score.download_count) / document.download_count
            score.relevance -= hoeffding_deviation(document.download_count)
            score.relevance = max(1e-6, score.relevance)
            
            score.commit(cursor, update=True)
        cursor.close()
        self._cnx.commit()

        
    def registerNode(self, nodeId, ip, port, bandwidth=None, lastSeenTime=None):
        # lastseentime param should probably never be used
        """this will be used as a callback in registrationclient/login"""
        print " ... registerNode %s:%s (%s)" % (ip, port, nodeId)
        if ip == "127.0.0.1":
            print " ... 127.0.0.1 is not an acceptable IP, we don't register this"
            return
        cursor = self._cnx.cursor()
        node = Node.selectOrInsertWhere(cursor, node_id=nodeId)[0]
        node.ip = ip
        node.node_id = nodeId
        node.port = port
        node.bandwidth = bandwidth or 1
        node.last_seen_time = lastSeenTime or int(time.time())
        node.commit(cursor, update=True)
        cursor.close()

    def registerNodeActivity(self, nodeId):
        """updates last_seen_time attribute"""
        cursor = self._cnx.cursor()
        nodes = Node.selectWhere(cursor, node_id=nodeId)
        if nodes:
            node = nodes[0]
            print " ... registerNodeActivity %s:%s (%s)" % (node.ip, node.port, nodeId)
            node.last_seen_time = int(time.time())
            node.commit(cursor, update=True)
        else:
            #FIXME: that's not a warning but a BUG 
            log.debug('No matching node found for id {%s}' % nodeId,
                      category='[warning]')
        cursor.close()

    def registerNodeInactivity(self, nodeId):
        """updates last_sleep_time attribute"""
        cursor = self._cnx.cursor()
        nodes = Node.selectWhere(cursor, node_id=nodeId)
        if nodes:
            node = nodes[0]
            node.last_sleep_time = int(time.time())
            node.commit(cursor, update=True)
        else:
            log.debug('No matching node found for id {%s}' % nodeId,
                      category='[warning]')
        cursor.close()        

    def getActiveNeighbors(self, nodeId, nbNodes):
        cursor = self._cnx.cursor() 
        nodes = Node.selectActive(cursor, nodeId, nbNodes) 
        cursor.close()
        return nodes

    def countResults(self, qid):
        """returns a couple (number of local results, number of distant results)
        for <qid>
        """
        cursor = self._cnx.cursor()
        try:
            subQuery = "SELECT * FROM results WHERE query_id='%s' GROUP BY document_id HAVING record_ts=MIN(record_ts)" % qid
            localCountQuery = "SELECT COUNT(*) FROM (%s) AS T WHERE T.host='localhost'" % subQuery
            distantCountQuery = "SELECT COUNT(*) FROM (%s) AS T WHERE T.host != 'localhost'" % subQuery
            cursor.execute(localCountQuery)
            localCount = cursor.fetchall()[0][0]
            cursor.execute(distantCountQuery)
            distantCount = cursor.fetchall()[0][0]
        finally:
            cursor.close()
        return localCount, distantCount

    def getQueryResults(self, query, onlyLocal=False, onlyDistant=False):
        """builds and returns Result' instances by searching in
        the temporary table built for <qid>
        """
        cursor = self._cnx.cursor()
        results = Result.selectWhere(cursor, query, onlyLocal, onlyDistant)
        cursor.close()
        return results

    def getProvidersFor(self, docId, qid):
        """returns a list of couples (ip, port) corresponding to
        each node that can provide the document.
        qid is needed only to avoid small conflicts with previous
        queries that returned the same documents
        (we don't want 'old' providers to appear in the list)
        """
        cursor = self._cnx.cursor()
        query = 'SELECT host, port FROM results WHERE query_id=%(qid)s ' \
                'AND document_id=%(docId)s'
        cursor.execute(query, locals())
        providers = cursor.fetchall()
        cursor.close()
        return providers
        
    def pushDocuments(self, qid, documents, provider):
        """push <documents> into the temporary table built for
        <qid>
        """
        cursor = self._cnx.cursor()
        try:
            for document in documents:
                res = Result.fromDocument(document, qid, provider)
                res.commit(cursor, update=False)
            cursor.close()
            self._cnx.commit()
        except:
            traceback.print_exc()
            self._cnx.rollback()

    def purgeOldResults(self):
        """removes old records in the results table"""
        tresholdDate = now() - ONE_HOUR
        query = 'DELETE FROM results WHERE record_ts < %(treshold)s'
        cursor = self._cnx.cursor()
        try:
            cursor.execute(query, {'treshold' : tresholdDate})
        except:
            traceback.print_exc()
            cursor.close()
            self._cnx.rollback()
        else:
            cursor.close()
            self._cnx.commit()
        
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
        try:
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
            self._cnx.commit()
        finally:
            cursor.close()
            self._cnx.rollback()
            traceback.print_exc()
        print "removed %d rows related to unreferenced documents" % rows
        return rows

    def getDocumentCount(self):
        """get document count"""
        try:
            cursor = self._cnx.cursor()
            docCounts = Document.getDocumentCount(cursor)
        finally:
            cursor.close()
        return docCounts

    def indexDocument(self, nodeId, futureDoc):
        """Inserts or update information in table documents,
        file_info, document_score and word
        :type nodeId: node_id or None if working locally
        """
        # XXX Decide if we can compute the content_hash and mime_type
        # ourselves or if the indexer should do it and
        # pass the values as an argument
        cursor = self._cnx.cursor()
        try:
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
            # update last seen time only if not working locally
            if nodeId is not None:
                provider = DocumentProvider.selectOrInsertWhere(cursor,
                                                                db_document_id=doc.db_document_id,
                                                                node_id=nodeId)[0]
                provider.last_providing_time = int(time.time())
                provider.commit(cursor, update=True)
                nodes = Node.selectWhere(cursor, node_id=nodeId)
                if not nodes:
                    self._cnx.rollback()
                    cursor.close()
                    raise ValueError('provider %s is not registered in our database !')
                node = nodes[0]
                node.last_seen_time = int(time.time())
                node.commit(cursor, update=True)
            cursor.close()
            self._cnx.commit()
        except:
            self._cnx.rollback()
            raise
    def _createDocument(self, cursor, futureDoc):

        doc = Document(document_id=futureDoc.content_hash,
                       title=futureDoc.title,
                       text=futureDoc.text[:MAX_STORED_SIZE],
                       size=futureDoc.fileSize,
                       publication_time=futureDoc.lastModificationTime,
                       download_count=0.,
                       url=base64.encodestring(futureDoc.filename), 
                       mime_type=futureDoc.mime_type,
                       matching=0.,
                       indexed='1',
                       state=futureDoc.state)
        doc.commit(cursor, update=False)
        doc = Document.selectWhere(cursor, document_id=futureDoc.content_hash)[0]
        return doc

def hoeffding_deviation(occurence, confidence=0.9):
     return sqrt(-mathlog(confidence / 2) / (2 * occurence))
