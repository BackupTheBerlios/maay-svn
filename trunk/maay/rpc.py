from time import time
from random import randint

from twisted.web.xmlrpc import XMLRPC
from twisted.cred.credentials import UsernamePassword
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer
## from twisted.python.failure import Failure

from logilab.common.db import get_dbapi_compliant_module

from maay.querier import MaayQuerier, IQuerier

def make_uid(username, password):
    """forge a unique identifier"""
    # FIXME: need a better implementation
    return long(hash(username+password) + hash(time()) + randint(-1000, 1000))


class MaayRPCServer(XMLRPC):

    def __init__(self, portal):
        XMLRPC.__init__(self)
        self._sessions = {}
        self.portal = portal
        self.dbapiMod = get_dbapi_compliant_module('mysql')
        
    def _attachUser(self, (interface, querier, logout), username, password):
        if interface is not IQuerier or querier is None:
            print "Could not get Querier for", username
            return '' # raise UnauthorizedLogin()
        digest = make_uid(username, password)
        self._sessions[digest] = querier
        return digest

    def xmlrpc_authenticate(self, username, password):
        """server authentication method"""
        print "call authenticate"
        creds = UsernamePassword(username, password)
        d = self.portal.login(creds, None, IQuerier)
        d.addCallback(self._attachUser, username, password)
        d.addErrback(lambda deferred: 'boom')
        print "done"
        return d

    def xmlrpc_lastIndexationTime(self, cnxId, filename):
        print "call lastIndexationTime"
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            fileInfos = querier.getFileInformations(filename)
            if len(fileInfos):
                time = fileInfos[0].file_time
            time = 0
        # XXX : could we return twisted.python.failure.Failure instance here ?
##         return Failure(ValueError("invalid connexion")
        time = -1 # XXX: need to differenciate bad cnxId and no last mod time
        print 'done'
        return time
    
    def xmlrpc_indexDocument(self, cnxId, filename, title, text, fileSize,
                             lastModifiedOn, content_hash, mime_type, state,
                             file_state):
        print "call indexDocument"
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            querier.indexDocument(filename, title, text, fileSize,
                             lastModifiedOn, content_hash, mime_type, state,
                             file_state)
        print "done"
        return 0
    
    def cnxIsValid(self, cnxId):
        if cnxId in self._sessions:
            return True
        print "We're under attack !"
        return False
