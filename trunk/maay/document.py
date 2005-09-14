"""this module provides a simple document abstraction"""

__revision__ = '$Id$'

import os

class Document:

    def __init__(self, docId, title, size, text, url="", mimetype="text"):
        self.title = title
        self.size = size
        self.text = text
        self.docId = docId or makeDocumentId(text)
        self.url = url
        self.mimetype = mimetype

    def readable_size(self):
        bytes = int(self.size)
        if bytes < 1000:
            return u'%s' % bytes
        elif 1000 < bytes < 10**6:
            return u'%s kB' % (bytes / 1000)
        elif 10**6 < bytes < 10**9:
            return u'%s MB' % (bytes / 10**6)
        else:
            return u'%s GB' % (bytes / 10**9)

    def get_abstract(self):
        return self.text[:200]
    abstract = property(get_abstract)

    def insertQuery(self):
        """generates an appropriate SQL insert query"""
        query = """INSERT INTO documents (document_id, mime_type, title, size, text)
        VALUES (%(docId)s, %(mimetype)s, %(title)s, %(size)s, %(text)s)"""
        args = dict(self.__dict__)
        return query, args
        
    

REMOVED_FILE_STATE = 0
CREATED_FILE_STATE = 1
MODIFIED_FILE_STATE = 2
UNMODIFIED_FILE_STATE = 3
NOT_INDEXED_FILE_STATE = 4

class FileInfo:
    def __init__(self, file_name, file_time, db_document_id, state, file_state):
        self.file_name = file_name
        self.file_time = file_time
        self.db_document_id = db_document_id
        self.state = state
        self.file_state = file_state

    def __str__(self):
        return "FileInfo: file_name=%s, file_time=%s, db_document_id=%s, state=%s, file_state=%s" % (self.file_name, self.file_time, self.db_document_id, self.state, self.file_state)

def makeDocumentId(filename):
    content = file(filename, 'rb').read()
    return sha.sha(content).hexdigest()
    
