import time
import threading
import binascii
import constants
import sys
import re
import random

import converter.texttools

import maay.datastructure.documentinfo
import maay.datastructure.documentscore
import maay.datastructure.documentprovider
import maay.datastructure.nodeinfo
import maay.datastructure.nodeinterest
import maay.datastructure.wordinfo
import maay.datastructure.fileinfo

import globalvars

# TODO : optimize documentScores insert (make a transaction for it) and use precomputed queries.

def to_tuple_str(words):
    if len(words) == 1:
        return "('%s')" % words[0]
    return str(tuple(words))


class Database:
    def __init__(self, dbms, host = None, port = None, user = None, passwd = None, db = None, db_file = None, unix_socket = None):
        if dbms == 'mysql':
            try:
                import MySQLdb
            except ImportError:
                raise "MySQLdb driver module not found"
            if globalvars.logger:
                globalvars.logger.info("Opening connection to MySQL database %s" % db)
            if unix_socket:
                if passwd:
                    self.__connection = MySQLdb.Connect(host=host, user=user, passwd=passwd, db=db, unix_socket=unix_socket, named_pipe=1)
                else:
                    self.__connection = MySQLdb.Connect(host=host, user=user, db=db, unix_socket=unix_socket, named_pipe=1)
            else:
                if passwd:
                    self.__connection = MySQLdb.Connect(host=host, user=user, passwd=passwd, db=db)
                else:
                    self.__connection = MySQLdb.Connect(host=host, user=user, db=db)

            self.__db_random_function_name = "RAND"
            self.__escape_string = MySQLdb.escape_string
        elif dbms == 'sqlite':
            try:
                import sqlite
            except ImportError:
                raise "MySQLdb driver module not found"
            globalvars.logger.debug("Opening connection to SQLite database %s" % db_file)
            self.__connection = sqlite.connect(db_file)
            self.__db_random_function_name = "random"
            self.__escape_string = self.__sqlite_escape_string
        else:   
            globalvars.logger.debug("Unknown database %s" % dbms)
            # TODO: raise an exception

        self.__dbLock = threading.Lock()
        self.__execLock = threading.Lock()

        self.__change_db = 0

    def drop_tables(self):
        pass

    def create_tables(self):
        if globalvars.logger:
            globalvars.logger.debug("Create database !")
                            
        self.executeQuery("""
                CREATE TABLE documents (
                        db_document_id INTEGER PRIMARY KEY AUTO_INCREMENT, 
                        document_id CHAR(40) NOT NULL default '',
                        mime_type varchar(40) NOT NULL default '',
                        title varchar(255) default NULL,
                        size int(11) default NULL,
                        text text,
                        publication_time int(14) default NULL,
                        state CHAR,
                        download_count float NOT NULL default '0',
                        url varchar(255) NOT NULL default '',
                        matching float NOT NULL default '0',
                        indexed CHAR DEFAULT '1',
                        INDEX (document_id),
                        INDEX (url)
                );""")

    # TODO: finish this stat tables
    #       self.executeQuery("""
    #               CREATE TABLE user_stats (
    #                       node_id INTEGER PRIMARY KEY AUTO_INCREMENT, 
    #                       repository_size int(14) default NULL,
    #                       ip char(15) NOT NULL default '',
    #                       port smallint(11) NOT NULL default '0',
    #                       last_seen_time int(11) default NULL,
    #                       version varchar(255),
    #                       os varchar(255),
    #                       download_count int(11) NOT NULL default '0',
    #                       search_count int(11) NOT NULL default 0,
    #               );""")

        self.executeQuery("""
                CREATE TABLE document_providers (
                        db_document_id INTEGER NOT NULL,
                        node_id char(40) NOT NULL default '',
                        last_providing_time int(11) default NULL,
                        PRIMARY KEY  (db_document_id,node_id),
                        INDEX (db_document_id)
                );""")

        self.executeQuery("""
                CREATE TABLE document_scores (
                        db_document_id INTEGER NOT NULL,
                        word varchar(50) NOT NULL,
                        position int(11) NOT NULL default '-1',
                        download_count float NOT NULL default '0',
                        relevance float NOT NULL default '0',
                        popularity float NOT NULL default '0',
                        PRIMARY KEY  (db_document_id,word),
                        INDEX (db_document_id),
                        INDEX (word)
                );""")

        self.executeQuery("""
                CREATE TABLE files (
                        file_name varchar(255) NOT NULL,
                        file_time int(11) NOT NULL default '0',
                        db_document_id INT,
                        state tinyint,
                        file_state tinyint,
                        PRIMARY KEY (file_name),
                        INDEX (db_document_id)
                );""")

        self.executeQuery("""
                CREATE TABLE node_interests (
                        node_id char(40) NOT NULL,
                        word varchar(50) NOT NULL,
                        claim_count float NOT NULL default '0',
                        specialisation float NOT NULL default '0',
                        expertise float NOT NULL default '0',
                        PRIMARY KEY  (node_id,word),
                        INDEX (node_id)
                );""")

        self.executeQuery("""
                CREATE TABLE nodes (
                        node_id char(40) NOT NULL,
                        ip char(15) NOT NULL default '',
                        port smallint(11) NOT NULL default '0',
                        last_seen_time int(11) default NULL,
                        counter int(11) NOT NULL default '0',
                        claim_count float NOT NULL default '0',
                        affinity double NOT NULL default '0',
                        bandwidth int(11) NOT NULL default '0',
                        PRIMARY KEY (node_id)
                );""")

        self.executeQuery("""
                        CREATE TABLE words (
                        word varchar(50) NOT NULL,
                        claim_count float NOT NULL default '0',
                        download_count float NOT NULL default '0',
                        PRIMARY KEY  (word)
                );""")

    def __escape_id(self, string):
#               return sqlite.Binary(binascii.unhexlify(string))
#               return sqlite.Binary(string)
        return string

    def __unescape_id(self, string):
#               return binascii.hexlify(string)
        return string


    def __sqlite_escape_string(self, string):
        return re.sub("'", "''", string)

    def __sqlite_unescape_string(self, string):
#               return string
        return re.sub("''", "'", string)


    def executeQuery(self, query):
        self.__execLock.acquire()
        try:
            cursor = self.__connection.cursor()
            cursor.execute(query)
#                       self.__connection.commit()
    #               if self.__changeBeforeCommit < 0:
    #                       self.__changeBeforeCommit = constants.change_before_commit
        finally:
            self.__execLock.release()
        return cursor

    def executeSelectQuery(self, query):
        self.__change_db = 1
        return self.executeQuery(query)

    def executeUpdateQuery(self, query):
        self.__change_db = 1
        return self.executeQuery(query)

    def executeInsertQuery(self, query):
        self.__change_db = 1
        return self.executeQuery(query)

    def executeDeleteQuery(self, query):
        self.__change_db = 1
        return self.executeQuery(query)

    def __begin_transaction(self):
#               self.__dbLock.acquire()
#               self.__change_db = 0
        pass

    def __end_transaction(self):
#               if self.__change_db == 1:
#                       self.__connection.commit()
#               self.__dbLock.release()
        pass
        
    def close(self):
#               self.__begin_transaction()
#               self.__connection.commit()
#               self.__end_transaction()
        self.__connection.close()

    def commit(self):
        self.__begin_transaction()
        self.__execLock.acquire()
        self.__connection.commit()
        self.__execLock.release()
#               self.__connection.close()
#               self.__connection = MySQLdb.Connect(host=host, user=user, passwd=passwd, db=db, autocommit=1)
        self.__end_transaction()

    # to remove
    def hex2bin(self, s):
        return binascii.unhexlify(s)
#               return binascii.a2b_hex(s)

    # to delete
#       def bin2hex(self, s):
#               return s
#               return binascii.b2a_hex(s)

###############################################################################
# DOCUMENT INFO DATABASE FUNCTIONS
###############################################################################

    def __buildDocumentInfosForQuery(self, query):
        documentInfos = []
        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return documentInfos
            db_document_id, document_id, mime_type, title, size, text, publication_time, state, download_count, url, matching, indexed = row
            del row

            if not document_id:
                continue

            indexed = int(indexed)
            document_id = self.__unescape_id(document_id)
            state = int(state)
            matching = float(matching)
            

#                       publication_time = self.__toUnixTime(publication_time)
#                       file_time = self.__toUnixTime(file_time)

            documentInfos.append(maay.datastructure.documentinfo.DocumentInfo(db_document_id, document_id, mime_type, title, size, text, publication_time, state, download_count, url, matching, indexed))

    def insertDocumentInfo(self, documentInfo):
        # check if it exists first :
        title = self.__escape_string(documentInfo.title)
        text = self.__escape_string(documentInfo.text)
        document_id = self.__escape_id(documentInfo.document_id)
        url = documentInfo.url
        if url:
            url = self.__escape_string(documentInfo.url)
        else:
            url = ""
#               publication_time = self.__toDatabaseTime(documentInfo.publication_time)
#               file_time = self.__toDatabaseTime(documentInfo.file_time)

        self.__begin_transaction()
        cursor = self.executeInsertQuery(
                """INSERT INTO documents (document_id, mime_type, title, size, text, publication_time, state, download_count, url, indexed) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')
                """ %  (document_id, documentInfo.mime_type, title, documentInfo.size, text, documentInfo.publication_time, documentInfo.state, documentInfo.download_count, url, documentInfo.indexed))

        self.__end_transaction()

        # TODO: use mysql function to get this
        d = self.getDocumentInfo(document_id = documentInfo.document_id)
        documentInfo.db_document_id = d.db_document_id


    def updateDocumentInfo(self, documentInfo):
        query = ""
        try:
            # check if it exists first :

            title = self.__escape_string(documentInfo.title)

            if documentInfo.text:
                update_text = "text = '%s'," % self.__escape_string(documentInfo.text)
            else:
                update_text = ""
    #               publication_time = self.__toDatabaseTime(documentInfo.publication_time)
    #               document_id = self.__escape_id(documentInfo.document_id)

            url = documentInfo.url
            if url:
                url = self.__escape_string(documentInfo.url)
            else:
                url = ""


            query = """UPDATE documents
                            SET mime_type='%s',
                                    title = '%s',
                                    size = '%s', %s
                                    publication_time = '%s',
                                    state = '%s',
                                    download_count = '%s',
                                    url = '%s',
                                    matching = '%s',
                                    indexed = '%s'
                            WHERE db_document_id='%s' """ % (documentInfo.mime_type, title, documentInfo.size, update_text, documentInfo.publication_time, documentInfo.state, documentInfo.download_count, url, documentInfo.matching, documentInfo.indexed, documentInfo.db_document_id)

            self.__begin_transaction()
            self.executeUpdateQuery(query)
            self.__end_transaction()
        except:
            globalvars.logger.exception("")
            globalvars.logger.debug(query)

    def updateDocumentInfoFields(self, document_id = None, db_document_id = None, indexed = None):
        if db_document_id:
            predicates = " AND db_document_id='%s'" % db_document_id
        if document_id:
            predicates = " AND document_id='%s'" % document_id
            
        if indexed:
            setter = "indexed='%s'," % indexed
            
        setter = setter.rstrip(',')
                
        query = """UPDATE documents
                        SET %s
                        WHERE 1 %s""" % (setter, predicates)
        self.__begin_transaction()
        self.executeUpdateQuery(query)
        self.__end_transaction()


    def getDocumentMaxDBDocumentID(self):
        query = "SELECT MAX(db_document_id) FROM documents"
        self.__begin_transaction()
        cursor = self.executeQuery(query)
        row = cursor.fetchone()
        self.__end_transaction()

        if not row:
            return 0
        if not row[0]:
            return 0
        return int(row[0])


    def getDocumentInfos(self, db_document_id = None, document_id = None, words = None, url = None, search_range = None, indexed = None, get_text = 0):
        predicates = "1"
        if document_id:
            document_id = self.__escape_id(document_id)
            predicates += " AND d.document_id='%s'" % document_id
            
        if db_document_id:
            predicates += " AND d.db_document_id='%s'" % db_document_id

        if url:
            predicates += " AND d.url='%s'" % url

        if get_text == 1:
            text_proj = "d.text"
        else:
            text_proj = "NULL"

        if url:
            predicates += " AND d.url='%s'" % url
            
        if indexed:
            predicates += " AND d.indexed='%s'" % indexed
            

        if search_range:
            states = []
            if search_range & maay.datastructure.documentinfo.PUBLISHED_STATE:
                states.append(maay.datastructure.documentinfo.PUBLISHED_STATE)
            if search_range & maay.datastructure.documentinfo.CACHED_STATE:
                states.append(maay.datastructure.documentinfo.CACHED_STATE)
            if search_range & maay.datastructure.documentinfo.KNOWN_STATE:
                states.append(maay.datastructure.documentinfo.KNOWN_STATE)
            if search_range & maay.datastructure.documentinfo.PRIVATE_STATE:
                states.append(maay.datastructure.documentinfo.PRIVATE_STATE)
            if search_range & maay.datastructure.documentinfo.UNKNOWN_STATE:
                states.append(maay.datastructure.documentinfo.UNKNOWN_STATE)
            if len(states) > 1:
                predicates += " AND d.state in %s" % str(tuple(states))
            else:
                predicates += " AND d.state in (%s)" % states[0]
        

        if words:
            query = """SELECT d.document_id, d.title, d.size, %s, d.state, d.download_count, d.state, d.url, d.matching, d.indexed
                            FROM document_scores ds, documents d
                            WHERE %s AND ds.word in %s AND d.document_id = ds.document_id
                            GROUP BY document_id
                            HAVING count(ds.score) = %d""" % (text_proj, predicates, str(tuple(words)), len(words))
        else:
            query = "SELECT d.db_document_id, d.document_id, d.mime_type, d.title, d.size, %s, d.publication_time, d.state, d.download_count, d.url, d.matching, d.indexed FROM documents d WHERE %s" % (text_proj, predicates)
        documentInfos = self.__buildDocumentInfosForQuery(query)
        return documentInfos

    def getDocumentInfo(self, document_id = None, db_document_id = None, get_text = 1):
        documentInfos = self.getDocumentInfos(document_id = document_id, db_document_id = db_document_id, get_text=get_text)
        if len(documentInfos) == 0:
            return None
        return documentInfos[0]

    def getDocumentCount(self, state):

        query = """SELECT count(document_id)
                                FROM documents 
                                WHERE state='%s'""" % state

        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        row = cursor.fetchone()
        row = row and row[:]

        self.__end_transaction()

        if not row or not row[0]:
            return 0

        return int(row[0])

    def deleteDocumentScores(self, db_document_id = None, word = None):
        query = """DELETE FROM document_scores WHERE 1"""
        if db_document_id:
            query += " AND db_document_id='%s'" % db_document_id

        if word:
            query += " AND word='%s'" % word
        self.__begin_transaction()
        cursor = self.executeDeleteQuery(query)
        self.__end_transaction()


    def deleteDocumentInfos(self, db_document_id = None, document_id = None):
        query = """DELETE FROM documents WHERE 1"""
        if db_document_id:
            query += " AND db_document_id='%s'" % db_document_id

        if document_id:
            query += " AND document_id='%s'" % document_id
        self.__begin_transaction()
        cursor = self.executeDeleteQuery(query)
        self.__end_transaction()

    def getDocumentSizeSum(self, state):
        query = """SELECT sum(size)
                                FROM documents 
                                WHERE state='%s'""" % state

        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        row = cursor.fetchone()
        row = row and row[:]

        self.__end_transaction()

        if not row or not row[0]:
            return 0

        return int(row[0])

    def getRandomDocumentInfos(self, document_count):
        query = "SELECT document_id, mime_type, title, size, text, publication_time, state, download_count, url, matching FROM documents ORDER BY rand() LIMIT 0, %s" % document_count
        return self.__buildDocumentInfosForQuery(query)

#       def __compute_ranking_score(self, word_download_count, document_download_count, document_score_download_count, relevance, popularity, matching, state):
#               if state != documentinfo.KNOWN_STATE:
#                       relevance = document_score_document_download_count
#               return (relevance + 0.001) * (popularity + 0.001) * (matching + 0.001)

    def getBestDocumentInfos(self, words, min_score, result_count, search_range, document_count = None):
        documentInfos = []

        url = None
        
        old_words = words
        words = []
        for i in xrange(len(old_words)):
            w = old_words[i]
            if w.find("url:") == 0:
                url = w[len("url:"):]
            else:
                words.append(w)

        url_predicate = ""                      
        if url:
            url_predicate = "AND d.url='%s'" % url

        if len(words) == 1:
            wordsStr = "('%s')" % words[0]
        else:
            wordsStr = str(tuple(words))
            

        if search_range:
            states = []
            if search_range & maay.datastructure.documentinfo.PUBLISHED_STATE:
                states.append(maay.datastructure.documentinfo.PUBLISHED_STATE)
            if search_range & maay.datastructure.documentinfo.CACHED_STATE:
                states.append(maay.datastructure.documentinfo.CACHED_STATE)
            if search_range & maay.datastructure.documentinfo.KNOWN_STATE:
                states.append(maay.datastructure.documentinfo.KNOWN_STATE)
            if search_range & maay.datastructure.documentinfo.PRIVATE_STATE:
                states.append(maay.datastructure.documentinfo.PRIVATE_STATE)
            if len(states) > 1:
                qs = "AND d.state in %s" % str(tuple(states))
            else:
                qs = "AND d.state in (%s)" % states[0]
        else:
            qs = ""
            
        if result_count > 0:
            result_count_str = "LIMIT 0, %d" % result_count
        else:
            result_count_str = ""
            
        if document_count:
            extra_field = "count(*)"
        else:
            extra_field = "0"
            
        if len(words) > 0:
            q = """SELECT d.db_document_id, d.document_id, d.mime_type, d.title, d.size, d.text,
                    d.publication_time, d.state, d.download_count, d.url, d.matching, d.indexed,
                    sum((ds.relevance + 0.001) * (ds.popularity + 0.001) * (d.matching + 0.001)) AS score, %s
                    FROM documents d, document_scores ds 
                    WHERE 1 %s AND ds.db_document_id=d.db_document_id AND ds.word IN %s %s
                    GROUP BY ds.db_document_id 
                    HAVING count(ds.db_document_id) = %d 
                    ORDER BY score DESC %s""" % (extra_field, qs, wordsStr, url_predicate, len(words), result_count_str)
        else:
            q = """SELECT d.db_document_id, d.document_id, d.mime_type, d.title, d.size, d.text,
                    d.publication_time, d.state, d.download_count, d.url, d.matching, d.indexed,
                    d.matching AS score, %s
                    FROM documents d
                    WHERE 1 %s %s
                    ORDER BY score DESC %s""" % (extra_field, qs, url_predicate, result_count_str)


        self.__begin_transaction()
        cursor = self.executeSelectQuery(q)
        extra = 0
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                if document_count:
                    document_count[0] = extra
                return documentInfos
            db_document_id, document_id, mime_type, title, size, text, publication_time, state, download_count, url, matching, indexed, score, extra = row
            indexed = int(indexed)

            document_id = self.__unescape_id(document_id)
            state = int(state)
            documentInfo = maay.datastructure.documentinfo.DocumentInfo(db_document_id, document_id, mime_type, title, size, text, publication_time, state, download_count, url, matching, indexed)
            documentInfos.append(documentInfo)


###############################################################################
# DOCUMENT SCORES DATABASE FUNCTIONS
###############################################################################

    def getDocumentScores(self, db_document_id = None, words = None, order = None, document_score_count = 0):
        scores = []
        query = "SELECT db_document_id, word, position, download_count, relevance, popularity FROM document_scores WHERE 1"
        if db_document_id:
            query += " AND db_document_id='%s'" % db_document_id

        if words:
            if len(words) == 1:
                w = " ('%s')" % words[0]
            else:
                w = str(tuple(words))
            query += " AND word in %s" % w

        if order:
            query += " ORDER BY %s DESC" % order

        if document_score_count:
            query += " LIMIT 0, %s" % document_score_count

        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return scores
            db_document_id, word, position, download_count, relevance, popularity = row
            scores.append(maay.datastructure.documentscore.DocumentScore(db_document_id, word, position, download_count, relevance, popularity))

    def getDocumentScoresHT(self, db_document_id = None, words = None, order = None):

        scores = {}
        #query = "SELECT word, position, excerpt, download_count, relevance, popularity FROM document_scores WHERE document_id = '%s'" % document_id
        query = "SELECT db_document_id, word, position, download_count, relevance, popularity FROM document_scores WHERE 1"
        if db_document_id:
            query += " AND db_document_id='%s'" % db_document_id

        if words:
            if len(words) == 1:
                w = " ('%s')" % words[0]
            else:
                w = str(tuple(words))
            query += " AND word in %s" % w

        if order:
            query += " ORDER BY %s DESC" % order


        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return scores
            db_document_id, word, position, download_count, relevance, popularity = row
            del row
            scores[word] = maay.datastructure.documentscore.DocumentScore(db_document_id, word, position, download_count, relevance, popularity)


    def getBestRelevantDocumentScores(self, db_document_id, word_count):
        scores = []
        self.__begin_transaction()
        cursor = self.executeSelectQuery("SELECT word, position, download_count, relevance, popularity FROM document_scores WHERE db_document_id='%s' AND relevance > 0 ORDER BY relevance DESC LIMIT 0, %s" % (db_document_id, word_count))
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return scores
            word, position, download_count, relevance, popularity = row
            scores.append(maay.datastructure.documentscore.DocumentScore(db_document_id, word, position, download_count, relevance, popularity))

    def getDocumentScore(self, db_document_id, word):
        query = """SELECT position, download_count, relevance, popularity
                                FROM document_scores
                                WHERE db_document_id = '%s' AND word = '%s'
                                """ % (db_document_id, word)

        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        row = cursor.fetchone()
        row = row and row[:]

        self.__end_transaction()

        if not row:
            return None

        position, download_count, relevance, popularity = row

        return maay.datastructure.documentscore.DocumentScore(db_document_id, word, position, download_count, relevance, popularity)

    def insertDocumentScore(self, documentScore):

        query = """INSERT INTO document_scores(db_document_id, word, position, download_count, relevance, popularity) VALUES ('%s', '%s', '%s', '%s', '%s', '%s') """ % (documentScore.db_document_id, documentScore.word, documentScore.position, documentScore.download_count, documentScore.relevance, documentScore.popularity)
        self.__begin_transaction()
        self.executeInsertQuery(query)
        self.__end_transaction()


    def insertDocumentScores(self, documentScores):
        self.__begin_transaction()
        for documentScore in documentScores:
            query = """INSERT INTO document_scores(db_document_id, word, position, download_count, relevance, popularity) VALUES ('%s', '%s', '%s', '%s', '%s', '%s') """ % (documentScore.db_document_id, documentScore.word, documentScore.position, documentScore.download_count, documentScore.relevance, documentScore.popularity)
            self.executeInsertQuery(query)
#               self.__connection.commit()
        self.__end_transaction()


    def updateDocumentScore(self, documentScore):
        query = """UPDATE document_scores SET download_count='%s', relevance='%s', popularity='%s', position = '%s' WHERE db_document_id='%s' AND word='%s' """ % (documentScore.download_count, documentScore.relevance, documentScore.popularity, documentScore.position, documentScore.db_document_id, documentScore.word)
        self.__begin_transaction()
        self.executeUpdateQuery(query)
        self.__end_transaction()



###############################################################################
# NODE INFO DATABASE FUNCTIONS
###############################################################################


    def getBestNodeInfos(self, search_query, node_count):
        if len(search_query) == 1:
            search_query_str = "('%s')" % search_query[0]
        else:
            search_query_str = str(tuple(search_query))

        query = "SELECT node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth FROM nodes ORDER BY affinity DESC LIMIT 0, 100"

        nodeInfos = []
        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                break

            node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth = row

            nodeInfos.append(maay.datastructure.nodeinfo.NodeInfo(node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth))

        score_sum = 0.0

        scored_node_infos = []
        selected_nodes_infos = []

        for nodeInfo in nodeInfos:
            interests = self.getNodeInterests(words=nodeInfo.node_id)
            score = 0.0
            for interest in interests:
                for word in search_query:
                    distance = converter.texttools.levenshtein_distance(word, interest.word)
                    score += (float(interest.specialisation) * float(interest.expertise) * float(nodeInfo.affinity)) / (2 ** distance)
            scored_node_infos.append((nodeInfo, score))
            score_sum += score

        for i in xrange(min(node_count, len(nodeInfos))):
            r = random.random() * score_sum
            j = -1
            while r >= 0 and j < len(scored_node_infos) - 1:
                j += 1
                r -= scored_node_infos[j][1]

            selected_nodes_infos.append(scored_node_infos[j][0])
            score_sum -= scored_node_infos[j][1]
            scored_node_infos.remove(scored_node_infos[j])

        return selected_nodes_infos



    def getRandomNodeInfos(self, excluded_nodes, node_count):
        excluded_node_ids = [n.node_id for n in excluded_nodes]
        if len(excluded_node_ids) == 0:
            excluded_nodes_str = ""
        elif len(excluded_node_ids) == 1:
            excluded_nodes_str = "WHERE node_id NOT IN ('%s')" % excluded_node_ids[0]
        else:
            excluded_nodes_str = "WHERE node_id NOT IN %s" % str(tuple(excluded_node_ids))

        query = "SELECT node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth FROM nodes %s ORDER BY %s() LIMIT 0, %s" % (excluded_nodes_str, self.__db_random_function_name, node_count)
        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        nodeInfos = []
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return nodeInfos

            node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth = row
#                       last_seen_time = self.__toUnixTime(last_seen_time)
            nodeInfos.append(maay.datastructure.nodeinfo.NodeInfo(node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth))

    def getNodeInfo(self, node_id):
        self.__begin_transaction()
        cursor = self.executeSelectQuery(
                """SELECT ip, port, counter, last_seen_time, claim_count, affinity, bandwidth
                        FROM nodes
                        WHERE node_id='%s' """ % node_id)

        row = cursor.fetchone()
        row = row and row[:]
        self.__end_transaction()

        if not row:
            return None

        ip, port, counter, last_seen_time, claim_count, affinity, bandwidth = row
        return maay.datastructure.nodeinfo.NodeInfo(node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth)

    def getNodeInfoCount(self):
        nodeInfos = []
        self.__begin_transaction()
        cursor = self.executeSelectQuery("""SELECT count(node_id) FROM nodes""")
        row = cursor.fetchone()
        self.__end_transaction()
        return int(row[0])

    def getNodeInfos(self, ip = None, port = None):
        nodeInfos = []
        self.__begin_transaction()
        query = "SELECT node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth FROM nodes WHERE 1"
        if ip:
            query += " AND ip='%s'" % ip
        if port:
            query += " AND port='%s'" % port

        cursor = self.executeSelectQuery(query)
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return nodeInfos
            node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth = row
            nodeInfos.append(maay.datastructure.nodeinfo.NodeInfo(node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth))

    def insertNodeInfo(self, nodeInfo):
#               last_seen_time = self.__toDatabaseTime(nodeInfo.last_seen_time)
        self.__begin_transaction()
        self.executeInsertQuery("""INSERT INTO nodes (node_id, ip, port, last_seen_time, counter, claim_count, bandwidth) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s')""" % (nodeInfo.node_id, nodeInfo.ip, nodeInfo.port, nodeInfo.last_seen_time, nodeInfo.counter, nodeInfo.claim_count, nodeInfo.bandwidth))
        self.__end_transaction()



    def updateNodeInfo(self, nodeInfo):
#               last_seen_time = self.__toDatabaseTime(nodeInfo.last_seen_time)
        query = "UPDATE nodes SET ip='%s', port='%s', counter='%s', last_seen_time='%s', claim_count='%s', affinity='%s', bandwidth='%s' WHERE node_id='%s'" % (nodeInfo.ip, nodeInfo.port, nodeInfo.counter, nodeInfo.last_seen_time, nodeInfo.claim_count, nodeInfo.affinity, nodeInfo.bandwidth, nodeInfo.node_id)
        self.__begin_transaction()
        self.executeUpdateQuery(query)
        self.__end_transaction()

    def getBestProviderNodeInfos(self, document_id, node_count):
        document_id = self.__escape_id(document_id)
        query = "SELECT n.node_id, n.ip, n.port, n.last_seen_time, n.counter, n.claim_count, n.affinity, n.bandwidth FROM nodes n, document_providers dp WHERE n.node_id=dp.node_id AND dp.document_id='%s' ORDER BY dp.last_providing_time DESC LIMIT 0, %d" % (document_id, node_count)
        nodeInfos = []

        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return nodeInfos

            node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth = row
#                       last_seen_time = self.__toUnixTime(last_seen_time)
            nodeInfos.append(maay.datastructure.nodeinfo.NodeInfo(node_id, ip, port, counter, last_seen_time, claim_count, affinity, bandwidth))


###############################################################################
# DOCUMENT PROVIDER DATABASE FUNCTIONS
###############################################################################

    def getDocumentProviders(self, db_document_id):
        query = """SELECT node_id, last_providing_time FROM document_providers WHERE db_document_id='%s'""" % db_document_id
        documentProviders = []

        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)

        while True:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return documentProviders
            node_id, last_providing_time = row
#                       last_providing_time = self.__toUnixTime(last_providing_time)
            documentProviders.append(maay.datastructure.documentprovider.DocumentProvider(db_document_id, node_id, last_providing_time))
            
    def getDocumentProvider(self, db_document_id, node_id):
        query = """SELECT last_providing_time FROM document_providers WHERE db_document_id='%s' AND node_id='%s'""" % (db_document_id, node_id)
        documentProviders = []

        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)

        row = cursor.fetchone()
        row = row and row[:]

        self.__end_transaction()
        if not row:
            return None
        last_providing_time = row[0]
#               last_providing_time = self.__toUnixTime(last_providing_time)
        return maay.datastructure.documentprovider.DocumentProvider(db_document_id, node_id, last_providing_time)



    def updateDocumentProvider(self, documentProvider):
#               last_providing_time = self.__toDatabaseTime(documentProvider.last_providing_time)
        query = """UPDATE document_providers SET last_providing_time='%s' WHERE db_document_id='%s' AND node_id='%s'""" % (documentProvider.last_providing_time, documentProvider.db_document_id, documentProvider.node_id)

        self.__begin_transaction()
        self.executeUpdateQuery(query)
        self.__end_transaction()

    def insertDocumentProvider(self, documentProvider):
        query = """INSERT INTO document_providers (db_document_id, node_id, last_providing_time) VALUES ('%s', '%s', '%s') """ % (documentProvider.db_document_id, documentProvider.node_id, documentProvider.last_providing_time)
        self.__begin_transaction()
        self.executeInsertQuery(query)
        self.__end_transaction()

    def deleteDocumentProvider(self, db_document_id=None, node_id=None):
        query = """DELETE FROM document_providers WHERE 1"""
        if db_document_id:
            query += " AND db_document_id='%s'" % db_document_id
        if node_id:
            query += " AND node_id='%s'" % node_id

        self.__begin_transaction()
        self.executeDeleteQuery(query)
        self.__end_transaction()




###############################################################################
# NODE INTEREST DATABASE FUNCTIONS
###############################################################################

    def updateNodeInterest(self, nodeInterest):
        self.__begin_transaction()
        self.executeUpdateQuery(
                """UPDATE node_interests
                        SET claim_count = '%s', specialisation='%s', expertise='%s'
                        WHERE node_id = '%s' AND word = '%s'
                        """ % (nodeInterest.claim_count, nodeInterest.specialisation, nodeInterest.expertise, nodeInterest.node_id, nodeInterest.word))
        self.__end_transaction()

    def insertNodeInterest(self, nodeInterest):
        self.__begin_transaction()
        self.executeInsertQuery(
                """INSERT INTO node_interests
                        (node_id, word, claim_count, specialisation, expertise)
                        VALUES ('%s', '%s', '%s', '%s', '%s')""" % (nodeInterest.node_id, nodeInterest.word, nodeInterest.claim_count, nodeInterest.specialisation, nodeInterest.expertise))

        self.__end_transaction()


    def getNodeInterest(self, node_id, word):
        query = """SELECT claim_count, specialisation, expertise FROM node_interests WHERE node_id='%s' AND word='%s'""" % (node_id, word)
        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        row = cursor.fetchone()
        row = row and row[:]
        self.__end_transaction()
        if row:
            claim_count, specialisation, expertise = row
            return maay.datastructure.nodeinterest.NodeInterest(node_id, word, claim_count, specialisation, expertise)

        return None

    def getNodeInterests(self, node_id=None, words=None):
        nodeInterests = []
        self.__begin_transaction()
        
        predicates = ""
        if node_id:
            predicates += " AND node_id='%s'" % node_id

        if words:
            predicates += " AND word in %s" % to_tuple_str(words)

        query = "SELECT node_id, word, claim_count, specialisation, expertise FROM node_interests WHERE 1 %s" % predicates
        
        cursor = self.executeSelectQuery(query)
        while 1:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return nodeInterests
            node_id, word, claim_count, specialisation, expertise = row
            nodeInterests.append(maay.datastructure.nodeinterest.NodeInterest(node_id, word, claim_count, specialisation, expertise))

    def getNodeInterestsHT(self, node_id):
        nodeInterests = {}
        self.__begin_transaction()
        cursor = self.executeSelectQuery("""SELECT word, claim_count, specialisation,expertise FROM node_interests WHERE node_id='%s'""" % node_id)
        while 1:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return nodeInterests
            word, claim_count, specialisation, expertise = row
            del row
            nodeInterests[word] = maay.datastructure.nodeinterest.NodeInterest(node_id, word, claim_count, specialisation, expertise)


###############################################################################
# WORD INFO DATABASE FUNCTIONS
###############################################################################


    # todo: if we want to optimize, create a function increaseInterest with
    # SQL : download_count = download_count + 1
    # => remove one access to database
    def getWordInfo(self, word):
        self.__begin_transaction()
        cursor = self.executeSelectQuery("""SELECT claim_count, download_count FROM words WHERE word='%s'""" % word)
        row = cursor.fetchone()
        row = row and row[:]
        self.__end_transaction()
        if row:
            claim_count, download_count = row
            return maay.datastructure.wordinfo.WordInfo(word, claim_count, download_count)
        return None

    def getWordSum(self):
        self.__begin_transaction()
        cursor = self.executeSelectQuery("""SELECT sum(claim_count), sum(download_count) FROM words""")
        row = cursor.fetchone()
        row = row and row[:]
        self.__end_transaction()
        if row:
            claim_count, download_count = row
            return (claim_count, download_count)
        return None
        
    def insertWordInfo(self, wordInfo):
        self.__begin_transaction()
        self.executeInsertQuery("""INSERT INTO words (word, claim_count, download_count) VALUES ('%s', '%s', '%s')""" % (wordInfo.word, wordInfo.claim_count, wordInfo.download_count))
        self.__end_transaction()
        
    def updateWordInfo(self, wordInfo):
        self.__begin_transaction()
        cursor = self.executeUpdateQuery("""UPDATE words SET claim_count='%s', download_count='%s' WHERE word='%s'""" % (wordInfo.claim_count, wordInfo.download_count, wordInfo.word))
        self.__end_transaction()

    def getWordInfos(self):
        wordInfos = []
        self.__begin_transaction()
        cursor = self.executeSelectQuery(
                """SELECT word, claim_count, download_count FROM words""")
        while 1:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return wordInfos
            word, claim_count, download_count = row
            wordInfos.append(maay.datastructure.wordinfo.WordInfo(word, claim_count, download_count))



###############################################################################
# FILE INFO DATABASE FUNCTIONS
###############################################################################

    def getFileInfos(self, file_name = None, file_state = None, state = None, db_document_id = None, order_by_filename = 0, file_name_sup = None, limit = None):
        query = "SELECT file_name, file_time, db_document_id, state, file_state FROM files WHERE 1"

        if file_name:
            file_name = self.__escape_string(file_name)
            query += " AND file_name='%s'" % file_name

        if file_name_sup:
            file_name_sup = self.__escape_string(file_name_sup)
            query += " AND file_name > '%s'" % file_name_sup

        if file_state:
            query += " AND file_state='%s'" % file_state
        if state:
            query += " AND state='%s'" % state
        if db_document_id:
            query += " AND db_document_id='%s'" % db_document_id
            
        if order_by_filename == 1:
            query += " ORDER BY file_name"
            
        if limit:
            query += " LIMIT %d,%d" % limit
        self.__begin_transaction()
        cursor = self.executeSelectQuery(query)
        fileInfos = []
        while 1:
            row = cursor.fetchone()
            if not row:
                self.__end_transaction()
                return fileInfos
            file_name, file_time, db_document_id, state, file_state = row
            file_name = self.__sqlite_unescape_string(file_name)

            fileInfos.append(maay.datastructure.fileinfo.FileInfo(file_name, file_time, db_document_id, state, file_state))
    

    def updateFileInfo(self, fileInfo):
        file_name = self.__escape_string(fileInfo.file_name)
        self.__begin_transaction()
        self.executeUpdateQuery("UPDATE files SET file_time='%s', db_document_id='%s', state='%s', file_state='%s' WHERE file_name='%s'" % (fileInfo.file_time, fileInfo.db_document_id, fileInfo.state, fileInfo.file_state, file_name))
        self.__end_transaction()

    def insertFileInfo(self, fileInfo):
        file_name = self.__escape_string(fileInfo.file_name)
        self.__begin_transaction()
        self.executeInsertQuery("INSERT INTO files (file_name, file_time, db_document_id, state, file_state) VALUES ('%s', '%s', '%s', '%s', '%s')" % (file_name, fileInfo.file_time, fileInfo.db_document_id, fileInfo.state, fileInfo.file_state))
        self.__end_transaction()

    def deleteFileInfos(self, file_name=None, file_state=None, state=None):
        if file_name:
            file_name = self.__escape_string(file_name)
            predicates = " AND file_name='%s'" % file_name
            
        if file_state:
            predicates = " AND file_state='%s'" % file_state

        if state:
            predicates = " AND state='%s'" % state

        self.__begin_transaction()
        self.executeInsertQuery("DELETE FROM files WHERE 1 %s" % predicates)
        self.__end_transaction()


    def resetRemovedFileInfoFileState(self, document_state):
        self.__begin_transaction()
        self.executeUpdateQuery("UPDATE files SET file_state='%d' WHERE state='%s'" % (maay.datastructure.fileinfo.REMOVED_FILE_STATE, document_state))
        self.__end_transaction()

    def deleteRemovedFileStateFileInfos(self):
        self.__begin_transaction()
        self.executeDeleteQuery("DELETE FROM files WHERE file_state='%d'" % maay.datastructure.fileinfo.REMOVED_FILE_STATE)
        self.__end_transaction()

    def removeDocument(self, document_id):
        documentInfo = self.getDocumentInfo(document_id)
        self.__begin_transaction()
        self.executeDeleteQuery("DELETE FROM documents where db_document_id='%s'" % documentInfo.db_document_id)
        self.executeDeleteQuery("DELETE FROM document_providers where db_document_id='%s'" % documentInfo.db_document_id)
        self.executeDeleteQuery("DELETE FROM files where db_document_id='%s'" % documentInfo.db_document_id)
        self.executeDeleteQuery("DELETE FROM document_scores where db_document_id='%s'" % documentInfo.db_document_id)
        self.__end_transaction()


    def executeDownloadAging(self):
        self.executeUpdateQuery("UPDATE words SET download_count=0.75*download_count")
        self.executeUpdateQuery("UPDATE documents SET download_count=0.75*download_count")
        self.executeUpdateQuery("UPDATE document_scores SET download_count=0.75*download_count")

    def executeClaimAging(self):
        self.executeUpdateQuery("UPDATE words SET download_count=0.75*download_count")
        self.executeUpdateQuery("UPDATE nodes SET claim_count=0.75*claim_count")
        self.executeUpdateQuery("UPDATE node_interests SET claim_count=0.75*claim_count")
