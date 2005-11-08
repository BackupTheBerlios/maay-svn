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

from time import time
from random import randint
import sys

from twisted.web.xmlrpc import XMLRPC
from twisted.cred.credentials import UsernamePassword, Anonymous
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer, reactor
## from twisted.python.failure import Failure

from maay.querier import MaayQuerier, IQuerier, ANONYMOUS_AVATARID, WEB_AVATARID
from maay.dbentity import FutureDocument, Document
from maay.p2pquerier import P2pQuerier, P2pQuery
from maay.query import Query

def make_uid(username, password):
    """forge a unique identifier"""
    # FIXME: need a better implementation
    return '%X' % abs(hash(username+password) + hash(time()) + randint(-1000, 1000))


class MaayRPCServer(XMLRPC):
    theP2pQuerier = None

    def __init__(self, nodeId, portal):
        XMLRPC.__init__(self)
        print "MaayRPCServer init %s %s" % (nodeId, portal)
        assert nodeId == portal.config.get_node_id ()
        self._sessions = {}
        self.portal = portal
        self.nodeId = portal.config.get_node_id() 
        self._sessions[WEB_AVATARID] = portal.webQuerier 
        self._sessions[ANONYMOUS_AVATARID] = portal.anonymousQuerier
        #self._p2pQuerier = P2pQuerier(nodeId, portal.webQuerier)
        MaayRPCServer.theP2pQuerier = P2pQuerier(nodeId, portal.webQuerier)

    def getP2pQuerier(self):
        assert (MaayRPCServer.theP2pQuerier) is not None
        return MaayRPCServer.theP2pQuerier
        
    def _attachUser(self, (interface, querier, logout), username, password):
        print "MaayRPCServer _attachUser", username, type(querier)
        if interface is not IQuerier or querier is None:
            errmsg = "Could not get Querier for", username
            print errmsg
            return '',  errmsg # raise UnauthorizedLogin()
        digest = make_uid(username, password)
        print " ... registering querier for %s (digest=%s)" % (username, digest)
        self._sessions[digest] = querier
        return digest, ''

    def xmlrpc_authenticate(self, username, password):
        """server authentication method"""
        print "MaayRPCServer xmlrpc_authenticate", username
        # anonymous login
        if (username, password) == ('', ''):
            creds = Anonymous()
            onSuccess = lambda d,u,p: (ANONYMOUS_AVATARID, '')
        else:
            creds = UsernamePassword(username, password)
            onSuccess = self._attachUser
        d = self.portal.login(creds, None, IQuerier)
        d.addCallback(onSuccess, username, password) # self._attachUser, username, password)
        d.addErrback(lambda failure: ('', str(failure)))
        return d

    def xmlrpc_lastIndexationTimeAndState(self, cnxId, filename):
        if self.cnxIsValid(cnxId):
            filename = unicode(filename)
            querier = self._sessions[cnxId]
            fileInfos = querier.getFileInformations(filename)
            if len(fileInfos):
                time = fileInfos[0].file_time
                state = fileInfos[0].state
            else:
                time = 0
                state = Document.UNKNOWN_STATE
        else:
            # XXX : could we return twisted.python.failure.Failure instance here ?
            ## return Failure(ValueError("invalid connexion")
            time = -1 # XXX: need to differenciate bad cnxId and no last mod time
            state = Document.UNKNOWN_STATE
        return time, state

    def xmlrpc_getIndexedFiles(self, cnxId):
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            return querier.getIndexedFiles()
        return []
        
    def xmlrpc_removeFileInfo(self, cnxId, filename):
        if self.cnxIsValid(cnxId):
            filename = unicode(filename)
            querier = self._sessions[cnxId]
            return querier.removeFileInfo(filename)
        return 0

    def xmlrpc_removeUnreferencedDocuments(self, cnxId):
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            return querier.removeUnreferencedDocuments()
        return -1

    def xmlrpc_indexDocument(self, cnxId, futureDoc):
        """
        :type title: xmlrpclib.Binary
        :type text: xmlrpclib.Binary
        """
        doc_dict = futureDoc
        futureDoc = FutureDocument()
        futureDoc.__dict__ = doc_dict
        futureDoc.filename = unicode(futureDoc.filename)
        futureDoc.title = unicode(futureDoc.title)
        try:
            futureDoc.text = unicode(futureDoc.text)
        except UnicodeError, exc:
            print exc
            print `text`
            return 1
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            querier.indexDocument(self.nodeId, futureDoc)

        return 0

    #def xmlrpc_distributedQuery(self, queryId, sender, ttl, words, mime_type):
    def xmlrpc_distributedQuery(self, queryDict):
        print "MaayRPCServer distributedQuery : %s " % queryDict
        query = P2pQuery(queryDict['id'],
                         queryDict['sender'],
                         queryDict['ttl'],
                         Query(queryDict['words'], filetype=queryDict['mime_type']))
        # schedule the query for later processing and return immediately
        # this enables the sender to query several nodes in a row
        d = reactor.callLater(.01, self.getP2pQuerier().receiveQuery, query)
        return self.nodeId

    def xmlrpc_distributedQueryAnswer(self, queryId, senderId, documents):
        print "MaayRPCServer distributedQueryAnswer : %s %s %s" % \
              (queryId, senderId, documents)
        answer = P2pAnswer(queryId, documents)
        d = reactor.callLater(.01, self.getP2pQuerier().sendAnswer, answer)
        return self.nodeId
                         
    
    def cnxIsValid(self, cnxId):
        if cnxId in self._sessions:
            return True
        print "MaayRPCServer cnxIsvalid Not !", cnxId
        return False
