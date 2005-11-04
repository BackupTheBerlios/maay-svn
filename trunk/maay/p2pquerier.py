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

# XXX should P2pQuery derive from query.Query?
class P2pQuery:
    def __init__(self, queryId, sender, ttl, query):
        """
        :param query: the query to wrap
        :type query: `maay.query.Query`
        """
        self.id = queryId
        self.sender = sender
        self.ttl = ttl
        self.query = query
        self.query.searchtype = 'p2p'
        self.documents = set()

    def hop(self):
        self.ttl -= 1

    def addMatch(self, document):
        self.documents.add(document.document_id)

    def isKnown(self, document):
        return document.document_id in self.documents
 
    def asKwargs(self):
        """return a dictionnary of arguments suitable for use as a
        **kwargs parameters to a call to distributedQuery"""
        # NOTE: We mustn't have None values in this dict because
        #       None can't be sent via XMLRPC.
        #       (Well, it can be in Twisted, but then I guess that
        #       we have to restrict to Twisted and Python world)
        return {'id':self.id,
                'sender':self.sender,
                'ttl':self.ttl,
                'words': self.query.words,
                'mime_type': self.query.filetype or '',
                }

class P2pAnswer:
    def __init__(self, queryId, documents):
        self.queryId = queryId
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
    _queries = {} 
    
    def __init__(self, nodeId, querier):
        self.nodeId = nodeId  
        self.querier = querier

    def sendQuery(self, query):
        for neighbor in self._selectTargetNeighbors(query):
            proxy = Proxy(neighbor.getRpcUrl())
            # below : returns a deferred
            d = proxy.callRemote('distributedQuery', query.asKwargs())
            d.addCallback(self.querier.registerNodeActivity)
            print "sent %s to %s" % (query, neighbor)

    def receiveQuery(self, query):
        if query.id in self._queries: 
            return
        
        self._queries[query.id] = query 

        query.hop()        
        if query.ttl > 0:
            self.sendQuery(query)

        documents = self.querier.findDocuments(query.query)
        self.receiveAnswer(P2pAnswer(query.id, documents))

    def receiveAnswer(self, answer, local=False):
        """record and forward answers to a query.
        If local is True, then the answers come from a local query,
        and thus must not be recorded in the database"""
        query = self._queries.get(answer.queryId)
        if query is None:
            return
        
        toSend = []
        
        for document in answer.documents:
            # TODO: record answer in database if local is False
            if not query.isKnown(document):
                self.query.addMatch(document)
                toSend.append(document.asDictionnary())
        
        if query.sender != self.nodeId:
            try:
                senderUrl = self.querier.getNodeUrl(query.sender)
                proxy = Proxy(senderUrl)
                d = proxy.callRemote('distributedQueryAnswer',
                                     query.id,
                                     self.nodeId,
                                     toSend)
                d.addCallback(self.querier.registerNodeActivity)
            except ValueError:
                print "unknown node %s" % query.sender
    
    def _selectTargetNeighbors(self, query):
        """return a list of nodes to which the query will be sent.
        """
        nbNodes = 2**(max(5, query.ttl))
        # TODO: use the neighbors' profiles to route requests
        return self.querier.getActiveNeighbors(self.nodeId, nbNodes)
        
