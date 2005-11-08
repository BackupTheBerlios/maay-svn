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

"""Management of distributed queries

"""
__revision__ = '$Id$'

from logilab.common.compat import set

from twisted.web.xmlrpc import Proxy

#TODO: add test for this
SEQ_DICT = {}

def incrementSequence(item):
    """Returns a growing monotone value for the
       associated item (starting from 0 when
       item is seen first)
    """
    if not SEQ_DICT.has_key(item):
        SEQ_DICT[item] = 0
    count = SEQ_DICT[item]
    SEQ_DICT[item] = count + 1
    return count


# XXX should P2pQuery derive from query.Query?
class P2pQuery:
    def __init__(self, sender, port, query, ttl=5, qid=None):
        """
        :param sender: really a nodeId
        :type sender: str
        :param port: the originator rpc port
        :type port: int
        :param query: the query to wrap
        :type query: `maay.query.Query`

        """
        if qid:
            self.qid = qid
        else:
            self.qid = incrementSequence(sender.__hash__)
        self.sender = sender
        self.port = port
        self.ttl = ttl
        self.query = query
        self.documents_ids = set()

    def hop(self):
        self.ttl -= 1

    def addMatch(self, document):
        self.documents_ids.add(document.document_id)

    def isKnown(self, document):
        return document.document_id in self.documents_ids
 
    def asKwargs(self):
        """return a dictionnary of arguments suitable for use as a
        **kwargs parameters to a call to distributedQuery"""
        # NOTE: We mustn't have None values in this dict because
        #       None can't be sent via XMLRPC.
        #       (Well, it can be in Twisted, but then I guess that
        #       we have to restrict to Twisted and Python world)
        return {'qid':self.qid,
                'sender':self.sender,
                'port':self.port,
                'ttl':self.ttl,
                'words': self.query.words,
                'mime_type': self.query.filetype or '',
                }

class P2pAnswer:
    def __init__(self, queryId, documents):
        self.queryId = queryId
        self.documents = documents

def sendQueryProblem(self, *args):
    """Politely displays any problem (bug, unavailability) related
    to an attempt to send a query.
    """
    print " ... problem sending the query :", args

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
    _receivedQueries = {} # key : queryId, val : query
    _sentQueries = {}     
    _answerCallbacks = []
    
    def __init__(self, nodeId, querier):
        self.nodeId = nodeId  
        self.querier = querier

    def sendQuery(self, query):
        """
        :type query: `maay.p2pquerier.P2pQuery`
        """        
        print "P2pQuerier sendQuery : %s" % query
        for neighbor in self._selectTargetNeighbors(query):
            proxy = Proxy(str(neighbor.getRpcUrl())) 
            d = proxy.callRemote('distributedQuery', query.asKwargs())
            d.addCallback(self.querier.registerNodeActivity)
            d.addErrback(sendQueryProblem)
            self._sentQueries[query.qid] = query
            print " ... sent to %s" % neighbor

    def addAnswerCallback(self, callback):
        P2pQuerier._answerCallbacks.append(callback)

    def _notifyAnswerCallbacks(self, results):
        for cb in P2pQuerier._answerCallbacks:
            apply(cb, results)

    def receiveQuery(self, query):
        """
        :type query: `maay.p2pquerier.P2pQuery`
        """
        print "P2pQuerier receiveQuery : %s" % query
        if query.qid in self._receivedQueries or \
           query.qid in self._sentQueries:
            print " ... we already know this query, this ends the trip"
            return
        
        self._receivedQueries[query.qid] = query 

        query.hop()        
        if query.ttl > 0:
            self.sendQuery(query)

        documents = self.querier.findDocuments(query.query)
        self.relayAnswer(P2pAnswer(query.qid, documents))

    def relayAnswer(self, answer, local=False): # local still unused
        """record and forward answers to a query.
        If local is True, then the answers come from a local query,
        and thus must not be recorded in the database"""
        print "P2pQuerier relayAnswer : %s documents" % len(answer.documents)
        query = self._receivedQueries.get(answer.queryId)
        if query is None: 
            print " ... bailing out : we had no query for this answer"
            return
        
        toSend = []
        
        for document in answer.documents:
            # TODO: record answer in database if local is False
            # auc : to cache them ?
            if not query.isKnown(document):
                query.addMatch(document)
                #toSend.append(document.asDictionnary())
                # above was meant to be like .asKwargs() ?
                # anyway, this stuff is xmlrpc-serializable (auc)
                toSend.append(document)
        
        if query.sender != self.nodeId: 
            try:
                # getNodeUrl seems not to exist yet
                #senderUrl = self.querier.getNodeUrl(query.sender)
                host = query.host 
                port = query.port
                print " ... will send answer to %s:%s" % (host, port)
                senderUrl = 'http://%s:%s' % (host, port)
                proxy = Proxy(senderUrl)
                d = proxy.callRemote('distributedQueryAnswer',
                                     query.qid,
                                     self.nodeId,
                                     toSend)
                d.addCallback(self.querier.registerNodeActivity)
            except ValueError:
                print "unknown node %s" % query.sender
        else: # local would be true ? don't waste the answers ...
            self._notifyAnswerCallbacks(toSend)
    
    def _selectTargetNeighbors(self, query):
        """return a list of nodes to which the query will be sent.
        """
        nbNodes = 2**(max(5, query.ttl))
        # TODO: use the neighbors' profiles to route requests
        return self.querier.getActiveNeighbors(self.nodeId, nbNodes)
        
