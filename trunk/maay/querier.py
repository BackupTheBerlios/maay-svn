"""provides the MaayQuerier class"""

__revision__ = '$Id$'
__metaclass__ = type

from mimetypes import guess_type

from logilab.common.db import get_connection
from maay.document import Document, FileInfo

class MaayQuerier:
    def __init__(self, driver='mysql', host='', database='', user='', password=''):
        self._cnx = get_connection(driver, host, database, user, password)


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
        args = {'words' : '(' + ','.join([repr(word) for word in words]) + ')',
                'lenwords' : len(words)}
        # XXX: what is the HAVING clause supposed to do ?
        query = """SELECT D.document_id, D.title, D.size, D.text, D.url, D.mime_type
                    FROM documents D, document_scores DS 
                    WHERE DS.db_document_id=D.db_document_id AND DS.word IN %(words)s
                    GROUP BY DS.db_document_id
                    HAVING count(DS.db_document_id) = %(lenwords)s"""
        print "QUERY =", query % args
        results = [Document(*row) for row in self._execute(query, args)]
        return results


    def getFilesInformations(self, file_name=None, file_state=None, state=None,
                             db_document_id=None, order_by_filename=0, file_name_sup=None, limit=None):
        query = "SELECT file_name, file_time, db_document_id, state, file_state FROM files"
        wheres = []
        if file_name:
            file_name = self.__escape_string(file_name)
            wheres.append("file_name='%s'" % file_name)
        if file_name_sup:
            file_name_sup = self.__escape_string(file_name_sup)
            wheres.append("file_name > '%s'" % file_name_sup)
        if file_state:
            wheres.append("file_state='%s'" % file_state)
        if state:
            wheres.append("state='%s'" % state)
        if db_document_id:
            wheres.append("db_document_id='%s'" % db_document_id)
        if wheres:
            query += ' WHERE %s' % (' AND '.join(wheres))
        if order_by_filename == 1:
            query += ' ORDER BY file_name'
            query += " LIMIT %d,%d" % limit
        return [FileInfo(*row) for row in self._execute(query)]


    def insertDocument(self, filename, title, text, fileSize, lastModTime):
        mimetype = guess_type(filename)[0]
        doc = Document(title, fileSize, text, url=None, mimetype=mimetype)
        query, args = doc.insertQuery()
        self._execute(query, args)
        
