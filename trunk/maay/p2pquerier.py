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

"""Management of distributed queries

"""
__revision__ = '$Id$'

import sha
import platform
import time
import os
import socket
import base64
from threading import Thread

from logilab.common.compat import set

from twisted.web.xmlrpc import Proxy
from twisted.internet import reactor
from maay.texttool import makeAbstract, removeSpace, untagText
from maay.query import Query
from maay.localinfo import NODE_LOGIN, NODE_HOST
from maay.configuration import NODE_CONFIG

QUERIER = None

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
#  - 50 results per node with a good ranking system (duh!) is
#    acceptable
#  - it should lightweight the network
LIMIT = 50

class P2pQuery:

    _version = 3
    
    def __init__(self, sender, query, ttl=5,
                 client_host=None, client_port=None):
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
        self.client_port = client_port or NODE_CONFIG.rpcserver_port

    #### qid accessors

    def setqid(self, qid):
        raise NotImplemented

    def getqid(self):
        return self.query.qid

    qid = property(getqid, setqid)

    #### other stuff
        
    def hop(self):
        self.ttl -= 1

    def addMatch(self, document):
        self.documents_ids.add(document['document_id'])

    def isKnown(self, document):
        return document['document_id'] in self.documents_ids

    #### serialization 
 
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
        if not compatible(P2pQuery._version, dic['version']):
            print "******* Query Version Mismatch ********"
            print "(we don't understand queries version %s)" % dic['version']
            raise QueryVersionMismatch(query_version=dic['version'],
                                       local_version=P2pQuery._version)
        _query = Query(' '.join(dic['words']),
                       filetype=dic['mime_type'],
                       qid=dic['qid'])
        p2pquery = P2pQuery(sender=dic['sender'],
                            client_host=dic['client_host'],
                            client_port=dic['client_port'],
                            ttl=dic['ttl'],
                            query=_query)
        return p2pquery
    fromDict = staticmethod(fromDict)
    
    def getWords(self):
        return self.query.words


def compatible(localversion, distantversion):
    if distantversion < 2:
        return False
    return True

class P2pAnswer:
    def __init__(self, qid, provider, documents):
        """
        :type provider: 4-tuple (login, nodeID, IP, xmlrpc-port)
        """
        self.qid = qid
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
    _receivedQueries = {} # key : qid, val : query
    _sentQueries = {}

    def __init__(self, querier):
        self.querier = querier
        global QUERIER
        QUERIER = querier # yes, a global
        self._answerCallbacks = {}
        # now, read a config. provided value for EXPIRATION_TIME
        # and fire the garbage collector
        P2pQuerier._EXPIRATION_TIME = max(NODE_CONFIG.query_life_time,
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

    def addAnswerCallback(self, qid, callback):
        #print "P2pQuerier : registering callback (%s, %s) for results" \
        #      % (qid, callback)
        self._answerCallbacks.setdefault(qid, []).append(callback)

    def _notifyAnswerCallbacks(self, qid, provider, results):
        #print "P2pQuerier : we notify the callbacks"
        for cb in self._answerCallbacks.get(qid, []):
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
	    d.addErrback(sendQueryErrback(neighbor, self.querier))
            self._sentQueries[query.qid] = query
            print "     ... sent to %s:%s %s" % (neighbor.ip,
                                                 neighbor.port,
                                                 neighbor.node_id)

    def receiveQuery(self, query):
        """
        :type query: `maay.p2pquerier.P2pQuery`
        """
        if query.qid in self._receivedQueries or \
           query.qid in self._sentQueries:
            return

        if query.qid not in self._sentQueries:
            print "P2pQuerier receiveQuery : %s from %s:%s " \
                  % (query.getWords(), query.client_host, query.client_port)
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

        # provider is a 4-uple (login, node_id, IP, xmlrpc-port)
        provider = (NODE_LOGIN,
                    NODE_CONFIG.get_node_id(),
                    NODE_HOST,
                    NODE_CONFIG.rpcserver_port)
            
        self.relayAnswer(P2pAnswer(query.qid, provider, documents))

    def relayAnswer(self, answer): 
        """record and forward answers to a query."""
        print "P2pQuerier relayAnswer : %s document(s) from %s:%s" \
              % (len(answer.documents), answer.provider[2],
                 answer.provider[3])
        query = self._receivedQueries.get(answer.qid)
        if not query :
            query = self._sentQueries.get(answer.qid)
            if not query:
                print " ... bug or dos : we had no query for this answer"
                return
                
        toSend = []
        for document in answer.documents:
            if not isinstance(document, dict):
                document = document.__dict__
            # only node-local docs will exhibit their full pathname
            if 'url' in document:
                doc_url = base64.decodestring(document['url'])
                document['url'] = base64.encodestring(os.path.basename(doc_url))
            # TODO: record answer in database if local is False
            # auc : to have them in Document with state == KNOWN
            abstract = makeAbstract(document['text'], query.getWords())
            document['text'] = untagText(removeSpace(abstract))
            query.addMatch(document)
            toSend.append(document)

        if query.sender != NODE_CONFIG.get_node_id():
            self.querier.registerNodeActivity(answer.provider[1])
            (host, port) = (query.client_host, query.client_port)
            print " ... relaying Answer to %s:%s ..." % (host, port)
            senderUrl = 'http://%s:%s' % (host, port)
            proxy = Proxy(senderUrl)
            d = proxy.callRemote('distributedQueryAnswer',
                                 query.qid,
                                 NODE_CONFIG.get_node_id(),
                                 answer.provider,
                                 toSend) 
            d.addErrback(answerQueryErrback(query))
        else:
            print " ... originator : we got an answer !"
            self._notifyAnswerCallbacks(answer.qid, answer.provider, toSend)
    
    def _selectTargetNeighbors(self, query):
        """return a list of nodes to which the query will be sent.
        """
        nbNodes = 2**(max(5, query.ttl))
        # TODO: use the neighbors' profiles to route requests
        return self.querier.getActiveNeighbors(NODE_CONFIG.get_node_id(), nbNodes)
        

##### Custommized errbacks for send/answer ops

def sendQueryErrback(target, querier):
    """Politely displays any problem (bug, unavailability) related
       to an attempt to send a query.
    """
    ':type target: Node'
    def QP(failure):
        print " ... problem sending the query to %s:%s, trace = %s" \
              % (target.ip, target.port, failure.getTraceback())
        registerSleeping(target)
        querier.registerNodeInactivity(target.node_id)
    return QP


def answerQueryErrback(target):
    """Politely displays any problem (bug, unavailability) related
       to an attempt to answer a query.
    """
    ':type target: P2pQuery'
    def AP(failure):
        print " ... problem answering the query to %s:%s, trace = %s" \
              % (target.client_host, target.client_port, failure.getTraceback())
    return AP


##### Background task that probes periodically sleeping nodes

## The call chain :
##
## registerSleeping --(first to sleep ?)--> checkOldest --> backgroundProbe --> nodeSleeps
##                                          ^                             |
##                                          |                             |
##                                          +------(sleeping nodes ?)-----+

SLEEPING_NODES = {}
CHECK_DELAY = 20 # time in secs before we probe the oldest sleeping node


def registerSleeping(node):
    # beware that not on all platforms we get sub-second values with time()
    # in this case we risk collisions (checked on Linux & Win2003)
    print "registerSleeping node %s scheduled for sleep check" % node.node_id
    stamp = time.time()
    sleeping = len(SLEEPING_NODES)
    if sleeping == 0:
        reactor.callLater(CHECK_DELAY, checkOldest)
    SLEEPING_NODES [stamp] = node


def checkOldest():
    assert len(SLEEPING_NODES) > 0
    stamps = SLEEPING_NODES.keys()
    stamps.sort()
    old_stamp = stamps[0]
    old_node = SLEEPING_NODES[old_stamp]
    del SLEEPING_NODES[old_stamp]
    thread = Thread(target=backgroundProbe, args=(old_node, old_stamp))
    thread.start()


PROBE_COUNT = 0

def backgroundProbe(node, stamp):
    now = time.time()
    global PROBE_COUNT
    PROBE_COUNT += PROBE_COUNT
    if nodeSleeps(node.ip, node.port):
        # we reschedule it
        if not PROBE_COUNT % 250:
            print "backgroundProbe node at %s:%s was still sleeping" \
                  % (node.ip, node.port)
        now = time.time()
        SLEEPING_NODES[now] = node
    else:
        print "backgroundProbe node at %s:%s has awaken" \
              % (node.ip, node.port)
        QUERIER.registerNodeActivity(node.node_id)
    right_now = time.time()
    if len(SLEEPING_NODES) > 0:
        reactor.callLater(abs(CHECK_DELAY - right_now + now), checkOldest)


#socket.setdefaulttimeout(30)
def nodeSleeps(node_ip, node_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((node_ip, node_port))
        s.close()
    except socket.error, exc:
        return True 
    else:
        return False


