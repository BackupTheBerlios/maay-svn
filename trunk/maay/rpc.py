from time import time
from random import randint

from twisted.web.xmlrpc import XMLRPC
from twisted.cred.credentials import UsernamePassword
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer

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
        creds = UsernamePassword(username, password)
        d = self.portal.login(creds, None, IQuerier)
        d.addCallback(self._attachUser, username, password)
        d.addErrback(lambda deferred: 'boom')
        return d

    def xmlrpc_lastIndexationTime(self, cnxId, filename):
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            fileInfos = querier.getFilesInformations(file_name=filename)
            if len(fileInfos):
                return fileInfos[0].file_time
            return 0
        return -1 # XXX: need to differenciate bad cnxId and no last mod time


    def xmlrpc_updateDocument(self, cnxId, docId, filename, title, text,
                              links, offset, fileSize, lastModTime):
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            querier.udpateDocument(docId, filename, title, text, links,
                                   offset, fileSize, lastModTime)
        return False
    
    def xmlrpc_insertDocument(self, cnxId, docId, filename, title, text,
                              links, offset, fileSize, lastModTime):
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            querier.insertDocument(docId, filename, title, text,
                                   links, offset, fileSize, lastModTime)
        return None
    
    def cnxIsValid(self, cnxId):
        if cnxId in self._sessions:
            return True
        print "We're under attack !"
        return False
