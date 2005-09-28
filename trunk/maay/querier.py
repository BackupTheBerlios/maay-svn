# -*- coding: iso-8859-1 -*- 
"""provides the MaayQuerier class"""


__revision__ = '$Id$'
__metaclass__ = type

from mimetypes import guess_type
import re
import time

from zope.interface import Interface, implements

from logilab.common.db import get_dbapi_compliant_module

from maay.dbentity import Document, FileInfo, DocumentProvider, DocumentScore, \
     Word
from maay.texttool import normalizeText, WORDS_RGX


class MaayAuthenticationError(Exception):
    """raised on db authentication failure"""

    
class IQuerier(Interface):
    """defines the High-Level interface to Maay SQL database"""

    def findDocuments(words):
        """returns all Documents matching <words>"""

    def getFileInformations(filename):
        """returns a list of FileInfo's instances according
        to DB's content
        """

    def getIndexedFiles():
        """returns a list of indexed file names as strings
        """

    def indexDocument(filename, title, text, fileSize, lastModifiedOn,
                      content_hash, mime_type, state, file_state):
        """Inserts or update information in table documents,
        file_info, document_score and word"""

    def removeFileInfo(filename):
        """remove filename from the database `files` table"""

    def removeUnreferencedDocuments():
        """remove rows in `documents` table when no row in `files` or
        `document_providers` table reference them, as well as the
        corresponding `document_scores` rows"""
        
    def close():
        """closes the DB connection"""

        
class MaayQuerier:
    """High-Level interface to Maay SQL database.

    The Querier receives requests from other components to insert or
    read data in the SQL database and dutifully executes these
    requests"""
    
    implements(IQuerier)
    
    def __init__(self, host='', database='', user='', password='', connection=None):
        if connection is None:
            dbapiMod = get_dbapi_compliant_module('mysql')
            try:
                connection = dbapiMod.connect(host=host, database=database,
                                              user=user, password=password,
                                              unicode=True)
                # FIXME: find a better way to perform this operation
                # the autodetection of the charset guesses latin-1 and
                # this obviously does not work with unicode
                connection.charset='utf-8'
            except dpapiMod.OperationalError:
                raise MaayAuthenticationError("Failed to authenticate user %r"
                                              % user)
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
    
    def findDocuments(self, words):
        """Find all indexed documents containing all the words in the list"""
        try:
            cursor = self._cnx.cursor()
            return Document.selectContaining(cursor, words)
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

    def indexDocument(self, filename, title, text, fileSize, lastModifiedOn,
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
                                           state)
                doc = Document.selectWhere(cursor, document_id=content_hash)[0]

            fileinfo = FileInfo(db_document_id=doc.db_document_id,
                                 file_name=filename,
                                 file_time=lastModifiedOn,
                                 state=state,
                                 file_state=file_state)
            fileinfo.commit(cursor, update=False)

        self._updateScores(cursor, doc.db_document_id, text)
        cursor.close()
        self._cnx.commit()        
        
    def _createDocument(self, cursor, content_hash, title, text, fileSize,
                        lastModifiedOn, filename, state):
        doc = Document(document_id=content_hash,
                       title=title,
                       text=text,
                       size=fileSize,
                       publication_time=lastModifiedOn,
                       download_count=0.,
                       url=filename,
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
