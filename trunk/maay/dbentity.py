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

"""this module provides a simple document abstraction"""

__revision__ = '$Id$'
__all__ = ['Document', 'FileInfo', 'DocumentProvider', 'DocumentScore',
           'Word', 'Node', 'NodeInterest']

import re
from sets import Set

from maay.texttool import normalizeText, WORD_MIN_LEN, WORD_MAX_LEN

class DBEntity:
    attributes = []
    tableName = None
    key = (None, )
    
    def __init__(self, **values):
        for attrname, value in values.iteritems():
            assert attrname in self.attributes, 'Unknown attribute %s' % attrname
            setattr(self, attrname, value)
        for keyattr in self.key:
            assert keyattr in self.attributes, \
                   "invalid value for key: %s" % keyattr

    def buildStateDict(self):
        return dict([(attr, getattr(self, attr)) for attr in self.boundAttributes()])
    stateDict = property(buildStateDict, doc="current object's state")

    def boundAttributes(self):
        """returns the list of attributes for which a value is specified"""
        return [attr for attr in self.attributes if hasattr(self, attr)]

    def _selectQuery(cls, whereColumns=()):
        if whereColumns:
            wheres = ['%s=%%(%s)s' % (attr, attr) for attr in whereColumns]
            where =  ' WHERE ' + ' AND '.join(wheres)
        else:
            where = ''
        query = 'SELECT %s FROM %s%s' % (', '.join(cls.attributes),
                                                cls.tableName,
                                                where)
        return query
    _selectQuery = classmethod(_selectQuery)

    def selectWhere(cls, cursor, **args):
        query = cls._selectQuery(args.keys())
        cursor.execute(query, args)
        results = cursor.fetchall()
        return [cls(**dict(zip(cls.attributes, row))) for row in results]
    selectWhere = classmethod(selectWhere)

    def selectOrInsertWhere(cls, cursor, **args):
        """If the db contains entities matching the keyword arguments,
        return the list otherwise, first insert an entity matching the
        kw arguments, and return it.  The default values for the
        columns are used.
        """
        entities = cls.selectWhere(cursor, **args)
        if entities:
            return entities
        else:
            entity = cls(**args)
            entity.commit(cursor, update=False)
            return cls.selectOrInsertWhere(cursor, **args)
    selectOrInsertWhere = classmethod(selectOrInsertWhere)
    
    def commit(self, cursor, update=False):
        if update:
            query = self._updateQuery()
        else:
            query = self._insertQuery()
        try:
            cursor.execute(query, self.stateDict)
        except Exception, exc:
            print "commit error:", exc
            print query
            raise
        

    def _updateQuery(self):
        """generates an UPDATE query according to object's state"""
        attrClauses = ['%s=%%(%s)s' % (attr, attr) for attr in self.boundAttributes()]
        wheres = ['%s=%%(%s)s' % (keyattr, keyattr) for keyattr in self.key]
        where = ' AND '.join(wheres)
        query = 'UPDATE %s SET %s WHERE %s' % (self.tableName,
                                               ', '.join(attrClauses),
                                               where)
        return query

    def _insertQuery(self):
        """generates an INSERT query according to object's state"""
        values = ['%%(%s)s' % attr for attr in self.attributes
                  if hasattr(self, attr)]
        query = 'INSERT INTO %s (%s) VALUES (%s)' % (self.tableName,
                                                     ', '.join(self.boundAttributes()),
                                                     ', '.join(values))
        return query

    def buildElementsFromTable(cls, cursor):
        """returns a list of <cls>'s instances based on database content"""
        return cls.selectWhere(cursor)
    buildElementsFromTable = classmethod(buildElementsFromTable)
    
    def __str__(self):
        return '%s: %s' % (self.__class__.__name__,
                           ', '.join(['%s=%s' % (attr, getattr(self, attr))
                                      for attr in self.boundAttributes()]))
    def __repr__(self):
        return str(self)


class FutureDocument:
    """Represents a Document before it gets fed to the database"""
    attributes = ('filename', 'title', 'text', 'fileSize', 'lastModificationTime',
                  'content_hash', 'mime_type', 'state', 'file_state')

    def __init__(self, **values):
        for attrname, value in values.iteritems():
            assert attrname in self.attributes, 'Unknown attribute %s' % attrname
            setattr(self, attrname, value)


class Document(DBEntity):
    """Represent a Document in the database
    A Document is different from a file, because several files can store
    the same document

    Attributes:
    -----------
    
     * db_document_id (primary key): unique integer identifying the document

     * str document_id: SHA1 hash of the content of the document as a hex string

     * str mime_type: mime type string (max length = 40 chars)

     * str title: title of the document (max length = 255 chars)

     * int size: size in bytes
     
     * str text: textual content of the document, used to display excerpts
     
     * int publication_time: last modification date of the file
       containing the doc (in seconds since Epoch)
     
     * char state: see below
     
     * float download_count: sum of the weights of the downloads
     
     * str url: really contains the full pathname of the file (not an url)
     
     * float matching: defaults to 0
     
     * char indexed: defaults to '1'

    The state of a document can be (values in parenthesis give the
    French word used in the PhD thesis):

    * PUBLISHED_STATE (intentionnel): the document was put on purpose by
    the user in an indexed directory

    * CACHED_STATE (mis en cache): the document has been downloaded by
    the user using Maay. It is available on the hard drive, but can be
    suppressed if disk space needs to be reclaimed

    * KNOWN_STATE (connu): the document is known through answers to
    requests that have been received. The available profile is lacunar
    and only a few words are known

    * UNKNOWN_STATE (???): not documented in the thesis, has a strange
      value (1<<9) since it gets stored in a char or a signed byte
    """

    # Caution : in the maay.orig branch, this parameter gets stored as
    # a string containing a single integer, so values of state above 9
    # are lost
    # XXX: only PUBLISHED and PRIVATE states are correctly handled
    PRIVATE_STATE = 0 
    PUBLISHED_STATE = 1 # << 0

    CACHED_STATE = 1 << 1
    KNOWN_STATE = 1 << 2
    UNKNOWN_STATE = 1 << 9 ### FIXME : this gets stored in the
                            ### database as a char in table Document or
                            ### as a tinyint(4) in table files. Check
                            ### to see if you get 0 or something else.


    attributes = ('db_document_id', 'document_id', 'mime_type', 'title',
                  'size', 'text', 'publication_time', 'state', 'download_count',
                  'url', 'matching', 'indexed')
    tableName = 'documents'
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

    def _selectContainingQuery(cls, words, mimetype=None, offset=0, allowPrivate=False):
        words = [normalizeText(unicode(w))
                 for w in words
                 if WORD_MIN_LEN <= len(w) <= WORD_MAX_LEN]        
        # XXX mimetype handling is a HACK. It needs to be integrated
        #     nicely in order to handle any kind of restrictions easily
        if mimetype is not None:
            restriction = " AND D.mime_type=%s "
            restrictionParams = [unicode(mimetype)]
        else:
            restriction = ""
            restrictionParams = []
        if not allowPrivate:
            restriction += " AND D.state!=%s "
            restrictionParams.append(cls.PRIVATE_STATE)
        # Question: what is the HAVING clause supposed to do ?
        # Answer: we select all documents containing one of the words
        # that we are looking for, group them by their identifier, and
        # only keep those identifiers which appeared once for each word
        # we were looking for.
        # XXX: LIMIT clause should be optional
        query = ("SELECT D.db_document_id, "
                        "D.document_id, "
                        "D.title, "
                        "D.size, "
                        "D.text, "
                        "D.url, "
                        "D.mime_type, "
                        "D.publication_time "
                 "FROM documents D, document_scores DS "
                 "WHERE DS.db_document_id=D.db_document_id "
                 "AND DS.word IN (%s) "
                 " %s "
                 "GROUP BY DS.db_document_id "
                 "HAVING count(DS.db_document_id) = %%s "
                 "ORDER BY D.publication_time DESC "
                 "LIMIT 15 OFFSET %s" % \
                 (', '.join(['%s'] * len(words)), restriction, offset))
        return query, words + restrictionParams + [len(words)]

    _selectContainingQuery = classmethod(_selectContainingQuery)

    def selectContaining(cls, cursor, words, mimetype=None, offset=0, allowPrivate=False):
        if not words:
            return []
        query, params = cls._selectContainingQuery(words, mimetype,
                                                   offset=offset,
                                                   allowPrivate=allowPrivate)
        if query:
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [cls(**dict(zip(['db_document_id', 'document_id', 'title',
                                    'size', 'text', 'url', 'mime_type',
                                    'publication_time'],
                                   row)))
                    for row in results]
        else:
            return [] 
        
    selectContaining = classmethod(selectContaining)
    
class Result(Document):
    """Results are temporary relations created/destroyed on the fly
       they contain documents matching both local and distributed requests
    """
    attributes = ('db_document_id', 'document_id', 'mime_type', 'title',
                  'size', 'text', 'publication_time', 'url', 'host', 'port',
                  'login')
    tableName = None # will be provided at run-time

    def __init__(self, name, **values):
        Result.tableName = name
        DBEntity.__init__(self, **values)
        self._buildTemporary()

    def __del__(self):
        self._destroyTemporary()

    def _buildTemporary(self):
        query = ("CREATE TABLE `%s` ("
                    "`db_document_id` int(11) NOT NULL auto-increment,"
                    "`document_id` varchar(40) NOT NULL default '',"
                    "`mime_type` varchar(40) NOT NULL default '',"
                    "`title` varchar(255) default NULL,"
                    "`size` int(11) default NULL,"
                    "`text` text,"
                    "`publication_time` int(14) default NULL,"
                    "`local_pathname` varchar(255) NOT NULL default ''," # like url
                    "`host` varchar(15),"
                    "`port` int(11)," # check this
                    "`login` varchar(255),"
                    "PRIMARY KEY (`db_document_id`),"
                    "KEY `document_id` (`document_id`),"
                    "KEY `local_pathname` (`local_pathname`))"
                 "TYPE=MyISAM;")

    def _destroyTemporary(self):
        query = "DROP TABLE %s;" % Result.tableName

    

class FileInfo(DBEntity):
    """
    Attributes:
    -----------
    
     * str file_name (primary key): the absolute path to the file
     
     * int file_time: time of last modification of the file according
       to the filesystem
       
     * int db_document_id: unique integer identifying the document

     * int state: see DocumentInfo.state attribute

     * int file_state: value can be one of
       - REMOVED_FILE_STATE
       - CREATED_FILE_STATE
       - MODIFIED_FILE_STATE
       - UNMODIFIED_FILE_STATE
       - NOT_INDEXED_FILE_STATE
    """
    attributes = ('file_name', 'file_time', 'db_document_id',
                  'state', 'file_state')
    tableName = 'files'
    key = ('file_name',)
    
    REMOVED_FILE_STATE = 0
    CREATED_FILE_STATE = 1
    MODIFIED_FILE_STATE = 2
    UNMODIFIED_FILE_STATE = 3
    NOT_INDEXED_FILE_STATE = 4
    

class DocumentScore(DBEntity):
    """
    Attributes
    -----------

     * int db_document_id (primary key): unique integer identifying
    the document

     * str word (primary key) : the word for which the score is computed

     * int position : offset of the word (in bytes) from the beginning
    of the document (in the current implementation, this is the offset
    of the last occurence of the word)

     * float download_count: sum of the download weights divided by
    the length of the search queries

     * float relevance: higher values mean that the word is used to
    specify a given document among downlods
    
     * float popularity: higher values mean that the document is a
    good answer to a query including the word
    """
    attributes = ('db_document_id', 'word', 'position', 'download_count',
                  'relevance', 'popularity')
    tableName = 'document_scores'
    key = ('db_document_id', 'word')

class DocumentProvider(DBEntity):
    """
    Attributes
    -----------
    
     * int db_document_id (primary key): unique integer identifying
       the document
     
     * str node_id (primary key): SHA1 hash value identifying a node
       as a hex string
     
     * int last_providing_time: last time the document was provided by
       the provider
    """
    attributes = ('db_document_id', 'node_id', 'last_providing_time')
    tableName = 'document_providers'
    key = ('db_document_id', 'node_id')

class Word(DBEntity):
    """
    Attributes:
    -----------
    
     * str word: max length = MAX_WORD_SIZE = 50
     
     * float claim_count: sum(1/length_of_query) for all queries in
       which the word appears
     
     * fload download_count: sum of the weights of the downloads
       divided by the length of the queries
    """
    tableName = 'words'
    attributes = ('word', 'claim_count', 'download_count')
    key = ('word',)


class Node(DBEntity):
    """
    Attributes:
    -----------
    
     * str node_id: SHA1 hash hex string
     
     * str ip : dotted numeric ip address
     
     * int port: port number on which maay is listening
     
     * int last_seen_time: date in seconds since epoch
     
     * float claim_count: total number of messages received from node
     
     * double affinity: caracterisation of interests similar to the
       running node (values close to 1 ar better)
     
     * int bandwidth: bandwidth of the node
    """
    tableName = 'nodes'
    attributes = ('node_id', 'ip', 'port', 'last_seen_time', 'counter',
                  'claim_count', 'affinity', 'bandwidth')
    key = ('node_id',)

    def _selectRegisteredNodesQuery(cls):
        query = cls._selectQuery()
        query += " WHERE node_id != %s ORDER BY last_seen_time DESC LIMIT %s"
        return query
    
    _selectRegisteredNodesQuery = classmethod(_selectRegisteredNodesQuery)

    def selectRegistered(cls, cursor, currentNodeId, maxResults):
        query = cls._selectRegisteredNodesQuery()
        cursor.execute(query, (currentNodeId, maxResults))
        results = cursor.fetchall()
        return [cls(**dict(zip(cls.attributes, row))) for row in results]
    selectRegistered = classmethod(selectRegistered)

    def selectActive(cls, cursor, currentNodeId, maxResults):
        return cls.selectRegistered(cursor, currentNodeId, maxResults)
    selectActive = classmethod(selectActive)

    def getRpcUrl(self):
        return 'http://%s:%s' % (self.ip, self.port)


class NodeInterest(DBEntity):
    """
    Attributes:
    -----------
    
     * str node_id: SHA1 hash hex string
     
     * str word: word on which interest is computed

     * float claim_count:
     
     * float specialisation: interest of the node for a word compared
       to other words
     
     * float expertise: interest of the node for a word compared to
       other nodes
    """
    tableName = 'node_interests'
    attributes = ('node_id', 'word', 'claim_count',
                  'specialisation', 'expertise')
    key = ('node_id', 'word')

    

