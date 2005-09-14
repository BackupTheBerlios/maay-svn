from time import time
from random import randint

from twisted.web.xmlrpc import XMLRPC
from twisted.cred.credentials import UsernamePassword

from logilab.common.db import get_dbapi_compliant_module

from maay.querier import Querier

def make_uid(username, password):
    """forge a unique identifier"""
    # FIXME: need a better implementation
    return long(hash(username+password) + hash(time()) + randint(-1000, 1000))


class MaayRPCServer(XMLRPC):

    def __init__(self, dbhost, dbname):
        XMLRPC.__init__(self)
        self._sessions = {}
        self.dbhost = dbhost
        self.dbname = dbname
        self.dbapiMod = get_dbapi_compliant_module('mysql')

    def xmlrpc_authenticate(self, username, password):
        # XXX: use maayPortal to authenticate
        try:
            querier = Querier(host=self.dbhost, databse=self.dbname,
                              user=username, password=password)
        except self.dbapiMod.OperationalError:
            return ''
        # XXX: dummy implementation
        digest = make_uid(username, password)
        self._sessions[digest] = querier
        return digest

    def xmlrpc_lastIndexationTime(self, cnxId, filename):
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            fileInfos = querier.getFilesInformations(file_name=filename)
            if len(fileInfos):
                return fileInfos[0].file_time
            return 0
        return None # XXX: need to differenciate bad cnxId and no last mod time


    def xmlrpc_updateDocument(self, cnxId, docInfo):
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            querier.udpateDocument(filename, title, text, fileSize, lastModTime)
        return False
    
    def xmlrpc_insertDocument(self, cnxId, filename, title, text, fileSize, lastModTime):
        if self.cnxIsValid(cnxId):
            querier = self._sessions[cnxId]
            querier.insertDocument(filename, title, text, fileSize, lastModTime)
        return None
    
    def cnxIsValid(self, cnxId):
        if cnxId in self._sessions:
            return True
        print "We're under attack !"
        return False
