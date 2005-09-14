"""this module provides a simple document abstraction"""

__revision__ = '$Id$'

__all__ = ['Document', 'FileInfo', 'DocumentProvider', 'DocumentScore']

import os

class DBEntity:
    attributes = []
    tableName = None
    key = (None, )
    
    def __init__(self, **values):
        for attrname, value in values.iteritems():
            assert attrname in self.attributes
            setattr(self, attrname, value)
        for keyattr in self.key:
            assert keyattr in self.attributes, "invalid value for key: %s" % keyattr

    def buildStateDict(self):
        return dict([(attr, getattr(self, attr)) for attr in self.attribtutes])
    stateDict = property(buildStateDict, doc="current object's state")
    
    def commit(self, cursor, update=False):
        if update:
            query = self.updateQuery()
        else:
            query = self.insertQuery()
        cursor.execute(query, self.stateDict)
        

    def updateQuery(self):
        """generates an UPDATE query according to object's state"""
        attrClauses = ['%s=%%(%s)s' % (attr, attr) for attr in self.attributes
                       if getattr(self, attr, None)]
        wheres = ['%s=%%(%s)s' % (keyattr, keyattr) for keyattr in self.key]
        where = ' AND '.join(wheres)
        query = 'UPDATE %s SET %s WHERE %s' % (self.tableName, ', '.join(attrClauses),
                                               where)
        return query

    def insertQuery(self):
        """generates an INSERT query according to object's state"""
        values = ['%%(%s)s' % attr for attr in self.attributes
                  if getattr(self, attr, None)]
        query = 'INSERT INTO %s (%s) VALUES (%s)' % (self.tableName,
                                                     ', '.join(self.attributes),
                                                     ', '.join(values))
        return query

    def buildElementsFromTable(cls, cursor):
        """returns a list of <cls>'s instances based on database content"""
        query = "SELECT %s FROM %s" % (', '.join(cls.attributes), cls.tableName)
        cursor.execute(query)
        results = cursor.fetchall()
        return [cls(**dict(zip(cls.attributes, row))) for row in results]
    buildElementsFromTable = classmethod(buildElementsFromTable)
    
    def __str__(self):
        return '%s: %s' % (self.__class__.__name__,
                           ', '.join(['%s=%s' % (attr, getattr(self, attr))
                                      for attr in self.attributes]))

class Document(DBEntity):
    attributes = ('db_document_id', 'document_id', 'mime_type', 'title',
                  'size', 'text', 'publication_time', 'state', 'download_count',
                  'url', 'matching', 'index')
    tableName = 'document'
    key = ('db_document_id',)
    
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


class FileInfo(DBEntity):
    attributes = ('file_name', 'file_time', 'db_document_id',
                  'state', 'file_state')
    tableName = 'files'
    key = ('db_document_id',)
    

class DocumentScore(DBEntity):
    attributes = ('db_document_id', 'word', 'position', 'download_count',
                  'relevance', 'popularity')
    tableName = 'document_scores'
    key = ('db_document_id',)

class DocumentProvider(DBEntity):
    attributes = ('db_document_id', 'node_id', 'last_providing_time')
    tableName = 'document_providers'
    key = ('db_document_id',)

REMOVED_FILE_STATE = 0
CREATED_FILE_STATE = 1
MODIFIED_FILE_STATE = 2
UNMODIFIED_FILE_STATE = 3
NOT_INDEXED_FILE_STATE = 4
