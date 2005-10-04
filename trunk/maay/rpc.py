from time import time
from random import randint

from twisted.web.xmlrpc import XMLRPC
from twisted.cred.credentials import UsernamePassword
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer
## from twisted.python.failure import Failure

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
        self.node_id = portal.config.get_node_id()
        
    def _attachUser(self, (interface, querier, logout), username, password):
        if interface is not IQuerier or querier is None:
            errmsg = "Could not get Querier for", username
            print errmsg
            return '',  errmsg # raise UnauthorizedLogin()
        digest = make_uid(username, password)
        print "Registering querier for %s (digets=%s)" % (username, digest)
        self._sessions[digest] = querier
        return digest, ''

    def xmlrpc_authenticate(self, username, password):
        """server authentication method"""
        creds = UsernamePassword(username, password)
        d = self.portal.login(creds, None, IQuerier)
        d.addCallback(self._attachUser, username, password)
        d.addErrback(lambda failure: ('', str(failure)))
        return d

    def xmlrpc_lastIndexationTime(self, cnxId, filename):
        if self.cnxIsValid(cnxId):
            filename = unicode(filename)
            querier = self._sessions[cnxId]
            fileInfos = querier.getFileInformations(filename)
            if len(fileInfos):
                time = fileInfos[0].file_time
            else:
                time = 0
        else:
            # XXX : could we return twisted.python.failure.Failure instance here ?
            ## return Failure(ValueError("invalid connexion")
            time = -1 # XXX: need to differenciate bad cnxId and no last mod time
        return time

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
                    
    def xmlrpc_indexDocument(self, cnxId, filename, title, text, fileSize,
                             lastModifiedOn, content_hash, mime_type, state,
                             file_state):
        """
        :type title: xmlrpclib.Binary
        :type text: xmlrpclib.Binary
        """
        filename = unicode(filename)
        title = unicode(title)
        text = unicode(text)
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            querier.indexDocument(self.node_id, filename, title, text, fileSize,
                                  lastModifiedOn, content_hash, mime_type, state,
                                  file_state)
        return 0
    
    def cnxIsValid(self, cnxId):
        if cnxId in self._sessions:
            return True
        print "We're under attack !"
        return False
