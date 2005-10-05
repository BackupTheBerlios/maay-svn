# -*- coding: iso-8859-1 -*- 
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

from maay.dbentity import Document, FileInfo, DocumentProvider, DocumentScore, \
     Word, Node
from maay.texttool import normalizeText, WORDS_RGX

class MaayAuthenticationError(Exception):
    """raised on db authentication failure"""

    
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

    def indexDocument(nodeId, filename, title, text, fileSize, lastModifiedOn,
                      content_hash, mime_type, state, file_state):
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
        
    def registerNode(nodeId):
        """register the current running node in the database"""
        
    def close():
        """closes the DB connection"""

        
class MaayQuerier:
    """High-Level interface to Maay SQL database.

    The Querier receives requests from other components to insert or
    read data in the SQL database and dutifully executes these
    requests"""
    
    implements(IQuerier)
    
    def __init__(self, host='', database='', user='', password='', connection=None):
        print "hello ?"
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
            except Exception:
                import traceback
                traceback.print_exc()
                raise
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
    
    def findDocuments(self, query):
        """Find all indexed documents matching the query"""
        words = WORDS_RGX.findall(normalizeText(query.words))
        self._updateQueryStatistics(words)
        try:
            cursor = self._cnx.cursor()
            return Document.selectContaining(cursor, words, query.filetype)
        finally:
            cursor.close()

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
        rows = cursor.execute('DELETE FROM files WHERE file_name = %s', filename)
        cursor.close()
        self._cnx.commit()
        print "removed %s" % filename
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
                    FROM document_scores LEFT JOIN documents
                                   ON document_scores.db_document_id = documents.db_document_id
                    WHERE documents.db_document_id IS NULL"""
        rows += cursor.execute(query2)
        cursor.close()
        self._cnx.commit()
        print "removed %d rows related to unreferenced documents" % rows
        return rows

    def indexDocument(self, nodeId, filename, title, text, fileSize, lastModifiedOn,
                      content_hash, mime_type, state, file_state):
        """Inserts or update information in table documents,
        file_info, document_score and word"""
        # XXX Decide if we can compute the content_hash and mime_type
        # ourselves or if the indexer should do it and pass the values as an argument
        cursor = self._cnx.cursor()
        # insert or update in table file_info
        fileinfo = FileInfo.selectWhere(cursor,
                                        file_name=filename)
        if fileinfo:
            fileinfo = fileinfo[0]
            fileinfo.file_time = lastModifiedOn
            fileinfo.state = state
            fileinfo.file_state = file_state
            doc = Document.selectWhere(cursor,
                                       db_document_id=fileinfo.db_document_id)
            if not doc or doc[0].document_id!=content_hash :
                # no document was found or a document with another content
                # in both case, we create a new Document in database
                # (we don't want to modify the existing one, because it
                # can be shared by several files)
                doc = self._createDocument(cursor,
                                           content_hash,
                                           title,
                                           text,
                                           fileSize,
                                           lastModifiedOn,
                                           filename,
                                           mime_type,
                                           state)
                fileinfo.db_document_id = doc.db_document_id
            else:
                # document has not changed
                doc = doc[0]
                
            fileinfo.commit(cursor, update=True)
                
        else:
            # file unknown
            # try to find a Document with same hash value
            doc = Document.selectWhere(cursor, document_id=content_hash)
            if doc:
                doc = doc[0]
                doc.state = state
                doc.publication_time = max(doc.publication_time, lastModifiedOn)
                doc.commit(cursor, update=True)
            else:
                doc = self._createDocument(cursor,
                                           content_hash,
                                           title,
                                           text,
                                           fileSize,
                                           lastModifiedOn,
                                           filename,
                                           mime_type,
                                           state)
                doc = Document.selectWhere(cursor, document_id=content_hash)[0]

            fileinfo = FileInfo(db_document_id=doc.db_document_id,
                                 file_name=filename,
                                 file_time=lastModifiedOn,
                                 state=state,
                                 file_state=file_state)
            fileinfo.commit(cursor, update=False)

        self._updateScores(cursor, doc.db_document_id, text)
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
        
    def _createDocument(self, cursor, content_hash, title, text, fileSize,
                        lastModifiedOn, filename, mime_type, state):
        doc = Document(document_id=content_hash,
                       title=title,
                       text=text,
                       size=fileSize,
                       publication_time=lastModifiedOn,
                       download_count=0.,
                       url=filename,
                       mime_type=mime_type,
                       matching=0.,
                       indexed='1',
                       state=state)
        doc.commit(cursor, update=False)
        doc = Document.selectWhere(cursor, document_id=content_hash)[0]
        return doc

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
        _scores = DocumentScore.selectWhere(cursor, db_document_id=db_document_id)
        db_scores = {}
        while _scores:
            score = _scores.pop()
            db_scores[score.word] = score
        return db_scores

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

    def _updateQueryStatistics(self, words):
        # FIXME: update node_interests too
        cursor = self._cnx.cursor()
        for word in words:
            winfo = Word.selectOrInsertWhere(cursor, word=word)[0]
            winfo.claim_count += 1 / len(words)
            winfo.commit(cursor, update=True)
        cursor.close
        self._cnx.commit()

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
            winfo.download_count += 1/len(words)
            winfo.commit(cursor, update=True)

        for word,score in scores.iteritems():
            score.download_count = max(0, score.download_count) + 1/len(words)
            winfo_downloads = wordInfo[word].download_count
            
            score.popularity = score.download_count / winfo_downloads
            score.popularity -= hoeffding_deviation(winfo_downloads)
            
            score.relevance = score.download_count / document.download_count
            score.relevance -= hoeffding_deviation(document.download_count)
            
            score.commit(cursor, update=True)
        cursor.close()
        self._cnx.commit()


    def registerNode(self, nodeId, ip, port, bandwidth):
        cursor = self._cnx.cursor()
        node = Node.selectOrInsertWhere(cursor, node_id=nodeId)[0]
        node.ip = ip
        node.port = port
        node.bandwidth = bandwidth
        node.last_seen_time = int(time.time())
        node.commit(cursor, update=True)


def hoeffding_deviation(occurence, confidence=0.9):
     return sqrt(-log(confidence / 2) / (2 * occurence))
