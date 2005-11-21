#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Management of distributed queries

"""
__revision__ = '$Id$'

import sha
import platform
import time
import os
import socket

from logilab.common.compat import set

from twisted.web.xmlrpc import Proxy
from twisted.internet import reactor
from maay.texttool import makeAbstract, removeSpace, untagText
from maay.configuration import NodeConfiguration
from maay.query import Query

nodeConfig=NodeConfiguration()
nodeConfig.load()
NODE_HOST = socket.gethostbyname(socket.gethostname())
NODE_PORT = nodeConfig.rpcserver_port

def hashIt(item, uname=''.join(platform.uname())):
    hasher = sha.sha()
    hasher.update(uname)
    hasher.update('%s' % id(item))
    hasher.update('%s' % time.time())
    return hasher.hexdigest()

def getUserLogin():
    """uses os.getlogin() when available, and if not provides a simple
    (and *unreliable*) replacement.
    """
    try:
        return os.getlogin()
    except (OSError, AttributeError):
        # OSError can occur on some Linux platforms.
        # AttributeError occurs on any non-UNIX platform
        # try to make a rough guess ...
        for var in ('USERNAME', 'USER', 'LOGNAME'):
            guessed = os.environ.get(var)
            if guessed:
                return guessed
        # could not guess username, use host name
        return socket.gethostname()

class QueryVersionMismatch(Exception):
    """we beginning a versionning nightmare trip on queries
       maybe I'll be shot for this, but who knows"""
    def __init__(self, local_version, query_version):
        self.local_version = local_version
        self.query_version = query_version

# This variable is hardcoded for now and describes the maximum
# number of results relayed by each peer.
# This might cause the results to be very incomplete and it will
# be improved in the future, but for now:
#  - 50 results per node with a good ranking system is
#    acceptable
#  - it should lightweight the network
LIMIT = 50

class P2pQuery:

    _version = 2
    
    def __init__(self, sender, query, ttl=5,
                 qid=None, client_host=None, client_port=None):
        """
        :param sender: really a nodeId
        :type sender: str
        :param port: the originator rpc port
        :type port: int
        :param query: the query to wrap
        :type query: `maay.query.Query`
        :param qid: query identifier
        :type qid: str
        """
        if qid:
            self.qid = qid
        else:
            self.qid = hashIt(sender)
        self.sender = sender
        #self.port = originator_port
        self.ttl = ttl
        self.query = query
        # explicitly set the 'limit' attribute for P2P queries
        self.query.limit = LIMIT
        self.documents_ids = set()
        # *** client_{host, port} belong to the immediate client
        # *** default args are typically used from webapplication instantiation
        # *** but NOT at rpc level, where we MUST use the transmited values
        self.client_host = client_host or NODE_HOST
        self.client_port = client_port or NODE_PORT
        
    def hop(self):
        self.ttl -= 1

    def addMatch(self, document):
        self.documents_ids.add(document['document_id'])

    def isKnown(self, document):
        return document['document_id'] in self.documents_ids
 
    def asKwargs(self):
        """return a dictionnary of arguments suitable for use as a
        **kwargs parameters to a call to distributedQuery"""
        # NOTE: We mustn't have None values in this dict because
        #       None can't be sent via XMLRPC.
        #       (Well, it can be in Twisted, but then I guess that
        #       we have to restrict to Twisted and Python world)
        return {'qid':          self.qid,
                'sender':       self.sender,
                'client_host' : self.client_host,
                'client_port' : self.client_port,
                'ttl':          self.ttl,
                'words':        self.query.words,
                'mime_type':    self.query.filetype or '',
                'version' :     P2pQuery._version
                }

    def fromDict(dic):
        """dual of asKwargs"""
        if dic.has_key('version'):
            if dic['version'] > P2pQuery._version:
                print "******* Query Version Mismatch ********"
                print "(we don't understand queries version %s)" % dic['version']
                raise QueryVersionMismatch(query_version=dic['version'],
                                           local_version=P2pQuery._version)
        _query = Query(' '.join(dic['words']), filetype=dic['mime_type'])
        p2pquery = P2pQuery(qid=dic['qid'],
                            sender=dic['sender'],
                            client_host=dic['client_host'],
                            client_port=dic['client_port'],
                            ttl=dic['ttl'],
                            query=_query)
        return p2pquery
    fromDict = staticmethod(fromDict)
    
    def getWords(self):
        return self.query.words


class P2pAnswer:
    def __init__(self, queryId, provider, documents):
        """
        :type provider: 3-tuple (login, IP, xmlrpc-port)
        """
        self.queryId = queryId
        self.provider = provider
        self.documents = documents

class P2pQuerier:
    """The P2pQuerier class is responsible for managing P2P queries.

    The sendQuery method is called by the web interface to send a
    distributed query to other Maay nodes, and by the P2pQuerier
    itself to broadcast a query to other known nodes.

    Distributed queries answers are sent back to the requester, and
    the rpc server calls receiveQuery. This method will forward the
    query to other nodes if it has not exceeded its TTL, and query the
    and the answers are stored in the local database as well to update
    the statistical information available about the neighbors'
    documents.
    """
    _EXPIRATION_TIME = 10 # secs, this is a min default guard value
    _markedQueries = {}
    _receivedQueries = {} # key : queryId, val : query
    _sentQueries = {}

    def __init__(self, nodeId, querier):
        self.nodeId = nodeId  
        self.querier = querier
        self._answerCallbacks = {}
        # now, read a config. provided value for EXPIRATION_TIME
        # and fire the garbage collector
        P2pQuerier._EXPIRATION_TIME = max(nodeConfig.query_life_time,
                                          P2pQuerier._EXPIRATION_TIME)
        reactor.callLater(self._EXPIRATION_TIME, self._markQueries)

    ######## Stuff to remove old queries from cache
        
    def _markQueries(self):
        queries = self._receivedQueries.keys() + self._sentQueries.keys()
        stamp = time.time()
        for q in queries:
            if q not in self._markedQueries:
                self._markedQueries[q] = stamp
        reactor.callLater(self._EXPIRATION_TIME, self._expireQueries)
        reactor.callLater(self._EXPIRATION_TIME+1, self._markQueries)

    def _expireQueries(self):
        curtime = time.time()
        expiredQueries = []
        for q in self._markedQueries:
            if curtime - self._markedQueries[q] > self._EXPIRATION_TIME:
                expiredQueries.append(q)
                try:
                    del self._receivedQueries[q]
                except:
                    pass
                try:
                    del self._sentQueries[q]
                except:
                    pass
        for q in expiredQueries:
            del self._markedQueries[q]
        if len(expiredQueries) > 0:
            print "P2pQuerier garbage collected old queries : %s" % \
            expiredQueries

    ######### Callback ops (who to feed the results of a query)

    def addAnswerCallback(self, queryId, callback):
        print "P2pQuerier : registering callback (%s, %s) for results" \
              % (queryId, callback)
        self._answerCallbacks.setdefault(queryId, []).append(callback)

    def _notifyAnswerCallbacks(self, queryId, provider, results):
        for cb in self._answerCallbacks.get(queryId, []):
            cb(provider, results)

    ######### True p2p ops (send, receive, answer ...)

    def sendQuery(self, query):
        """
        :type query: `maay.p2pquerier.P2pQuery`
        """        
        print "P2pQuerier sendQuery %s : %s" % (query.qid, query)
        if self._sentQueries.has_key(query.qid):
            return
        print " ... query from %s:%s" % (query.client_host,
                                         query.client_port)
        for neighbor in self._selectTargetNeighbors(query):
            if (neighbor.ip, neighbor.port) == \
                   (query.client_host, query.client_port):
                continue
            proxy = Proxy(str(neighbor.getRpcUrl()))
            d = proxy.callRemote('distributedQuery', query.asKwargs())
            d.addCallback(self.querier.registerNodeActivity)
            d.addErrback(sendQueryErrback(neighbor, self.querier))
            self._sentQueries[query.qid] = query
            print "     ... sent to %s:%s %s" % (neighbor.ip,
                                                 neighbor.port,
                                                 neighbor.node_id)

    def receiveQuery(self, query):
        """
        :type query: `maay.p2pquerier.P2pQuery`
        """
        print "P2pQuerier receiveQuery : %s" % query
        if query.qid in self._receivedQueries or \
           query.qid in self._sentQueries:
            print " ... we already know query %s, this ends the trip" % query.qid
            return

        if query.qid not in self._sentQueries:
            print " ... %s is a new query, let's work ..." % query.qid
            self._receivedQueries[query.qid] = query 

        query.hop()        
        if query.ttl > 0:
            self.sendQuery(query)
        documents = self.querier.findDocuments(query.query)
        if len(documents) == 0:
            print " ... no document matching the query, won't answer."
            return
        
        for doc in documents:
            abstract = makeAbstract(doc.text, query.getWords())
            doc.text = untagText(removeSpace(abstract))

        # provider is a triple (login, IP, xmlrpc-port)
        provider = (getUserLogin(),
                    socket.gethostbyname(socket.gethostname()),
                    NODE_PORT)
            
        self.relayAnswer(P2pAnswer(query.qid, provider, documents))

    def relayAnswer(self, answer, local=False): # local still unused
        """record and forward answers to a query.
        If local is True, then the answers come from a local query,
        and thus must not be recorded in the database"""
        print "P2pQuerier relayAnswer : %s document(s)" % len(answer.documents)
        query = self._receivedQueries.get(answer.queryId)
        if not query :
            query = self._sentQueries.get(answer.queryId)
            if query:
                print " ... originator : we got an answer !"
            else:
                print " ... bug or dos : we had no query for this answer"
                return
        print " ... relaying Answer to %s:%s ..." \
              % (query.client_host, query.client_port)
        
        toSend = []
        for document in answer.documents:
            if not isinstance(document, dict):
                document = document.__dict__
                if 'url' in document:
                    document['url'] = os.path.basename(document['url'])
            # TODO: record answer in database if local is False
            # auc : to cache them ?
            if not query.isKnown(document):
                abstract = makeAbstract(document['text'], query.getWords())
                document['text'] = untagText(removeSpace(abstract))
                query.addMatch(document)
                toSend.append(document)
        
        if query.sender != self.nodeId: 
            try:
                (host, port) = (query.client_host, query.client_port)
                print " ... will send answer to %s:%s" % (host, port)
                senderUrl = 'http://%s:%s' % (host, port)
                proxy = Proxy(senderUrl)
                d = proxy.callRemote('distributedQueryAnswer',
                                     query.qid,
                                     self.nodeId,
                                     answer.provider,
                                     toSend) 
                d.addCallback(self.querier.registerNodeActivity)
                d.addErrback(answerQueryErrback(query))
            except ValueError:
                print " ... unknown node %s" % query.sender
        else: 
            self._notifyAnswerCallbacks(answer.queryId, answer.provider, toSend)
    
    def _selectTargetNeighbors(self, query):
        """return a list of nodes to which the query will be sent.
        """
        nbNodes = 2**(max(5, query.ttl))
        # TODO: use the neighbors' profiles to route requests
        return self.querier.getActiveNeighbors(self.nodeId, nbNodes)
        

##### Custommized errbacks for send/answer ops

def sendQueryErrback(target, querier):
    ':type target: Node'
    def QP(failure):
        """Politely displays any problem (bug, unavailability) related
        to an attempt to send a query.
        """
        print " ... problem sending the query to %s:%s, trace = %s" \
              % (target.ip, target.port, failure.getTraceback())
        querier.registerNodeInactivity(target.node_id)
    return QP

def answerQueryErrback(target):
    ':type target: P2pQuery'
    def AP(failure):
        """Politely displays any problem (bug, unavailability) related
        to an attempt to answer a query.
        """
        print " ... problem answering the query to %s:%s, trace = %s" \
              % (target.client_host, target.client_port, failure.getTraceback())
    return AP

