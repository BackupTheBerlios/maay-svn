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
from twisted.internet import defer
## from twisted.python.failure import Failure

from maay.querier import MaayQuerier, IQuerier, ANONYMOUS_AVATARID

def make_uid(username, password):
    """forge a unique identifier"""
    # FIXME: need a better implementation
    return '%X' % abs(hash(username+password) + hash(time()) + randint(-1000, 1000))


class MaayRPCServer(XMLRPC):

    def __init__(self, portal):
        XMLRPC.__init__(self)
        self._sessions = {}
        self.portal = portal
        self.node_id = portal.config.get_node_id()
        self._sessions[ANONYMOUS_AVATARID] = portal.anonymousQuerier
        
    def _attachUser(self, (interface, querier, logout), username, password):
        if interface is not IQuerier or querier is None:
            errmsg = "Could not get Querier for", username
            print errmsg
            return '',  errmsg # raise UnauthorizedLogin()
        digest = make_uid(username, password)
        print "Registering querier for %s (digest=%s)" % (username, digest)
        self._sessions[digest] = querier
        return digest, ''

    def xmlrpc_authenticate(self, username, password):
        """server authentication method"""
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
        try:
            text = unicode(text)
        except UnicodeError, exc:
            print exc
            print `text`
            return 1
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
