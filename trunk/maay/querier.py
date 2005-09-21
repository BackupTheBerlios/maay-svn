# -*- coding: iso-8859-1 -*- 
"""provides the MaayQuerier class"""


__revision__ = '$Id$'
__metaclass__ = type

from mimetypes import guess_type
import re
import time
from string import maketrans, translate

from zope.interface import Interface, implements
import MySQLdb

from maay.dbentity import Document, FileInfo, DocumentProvider, DocumentScore, \
     Word


WORD_MIN_LEN = 2
WORD_MAX_LEN = 50

MAX_STORED_SIZE = 65535
# XXX: need to handle diacritics signs
# according to the PhD thesis, we should substitute the diacritics
# chars with the non diacritics (e.g. révoltant -> revoltant)
# find a portable way to do this with unicode (good luck, Luke)
WORDS_RGX = re.compile(r'\w{%s,%s}' % (WORD_MIN_LEN, WORD_MAX_LEN)) 

class IQuerier(Interface):
    """defines the High-Level interface to Maay SQL database"""

    def findDocuments(words):
        """returns all Documents matching <words>"""

    def getFilesInformations(**wheres):
        """returns a list of FileInfo's instances according
        to DB's content
        """

    def indexDocument(filename, title, text, fileSize, lastModifiedOn,
                      content_hash, mime_type, state, file_state):
        """Inserts or update information in table documents,
        file_info, document_score and word"""

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
            connection = MySQLdb.connect(host=host, db=database,
                                         user=user, passwd=password)
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
        results = [Document(**dict(zip(columns, row)))
                   for row in self._execute(query, args)]
        return results


    def getFilesInformations(self, **args):
        cursor = self._cnx.cursor()
        results = FileInfo.selectWhere(cursor, filename=args['file_name'])
        cursor.close()
        return results

    def indexDocument(self, filename, title, text, fileSize, lastModifiedOn,
                      content_hash, mime_type, state, file_state):
        """Inserts or update information in table documents,
        file_info, document_score and word"""
        # XXX Decide if we can compute the content_hash and mime_type
        # ourselves or if the indexer should do it and pass the values as an argument
        cursor = self._cnx.cursor()

        # insert or update in table document
        doc = Document.selectWhere(cursor, document_id=content_hash)
        if not doc:
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
        else:
            #FIXME : update db
            pass

        # insert or update in table file_info
        files = FileInfo.selectWhere(cursor,
                                     db_document_id=doc.db_document_id,
                                     file_name=filename)
        if files:
            file_info = files[0]
            file_info.file_time = lastModifiedOn
            file_info.state = state
            file_info.file_state = file_state
            file_info.commit(cursor, update=True)
        else:
            file_info = FileInfo(db_document_id=doc.db_document_id,
                                 file_name=filename,
                                 file_time=lastModifiedOn,
                                 state=state,
                                 file_state=file_state)
            file_info.commit(cursor, update=False)

        self._updateScores(cursor, doc.db_document_id, text)
        cursor.close()


    def _updateScores(self, cursor, db_document_id, text):
        # insert or update in table document_score
        db_scores = self._getScoresDict(cursor, db_document_id)
        doc_scores = {}
        # We update the document_score table only for the first
        # occurence of the word in the document
        for match in WORDS_RGX.finditer(normalize_text(text)):
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

        
_table = maketrans(
                   '\xc0\xc1\xc2\xc3\xc4\xc5'
                   '\xc7'
                   '\xc8\xc9\xca\xcb'
                   '\xcc\xcd\xce\xcf'
                   '\xd0'
                   '\xd1'
                   '\xd2\xd3\xd4\xd5\xd6\xd8'
                   '\xd9\xda\xdb\xdc'
                   '\xdd'
                   '\xe0\xe1\xe2\xe3\xe4\xe5'
                   '\xe7'
                   '\xe8\xe9\xea\xeb'
                   '\xec\xed\xee\xef'
                   '\xf0'
                   '\xf1'
                   '\xf2\xf3\xf4\xf5\xf6\xf8'
                   '\xf9\xfa\xfb\xfc'
                   '\xff'
                   ,
                   'aaaaaa'
                   'c'
                   'eeee'
                   'iiii'
                   'o'
                   'n'
                   'oooooo'
                   'uuuu'
                   'y'
                   'aaaaaa'
                   'c'
                   'eeee'
                   'iiii'
                   'o'
                   'n'
                   'oooooo'
                   'uuuu'
                   'y'
                   )

def normalize_text(word, table=_table):
    """turns everything to lowercase, and converts accentuated
    characters to non accentuated chars."""
    word = word.lower()
    return translate(word, table)

del maketrans
del _table
