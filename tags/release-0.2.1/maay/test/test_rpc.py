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

"""unit tests for Maay's XMLRPC server

These test cases should be tested with the twisted's `trial` utility
"""

__revision__ = '$Id$'

# import unittest
from xmlrpclib import ServerProxy

from zope.interface import implements
from twisted.web import server, xmlrpc
from twisted.internet import reactor, defer
from twisted.trial import unittest
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.credentials import IUsernamePassword
from twisted.python.failure import Failure

from maay import rpc
from maay.dbentity import Document
from maay.querier import MaayQuerier, AnonymousQuerier, ANONYMOUS_AVATARID
from maay.server import MaayPortal
from maay.configuration import WebappConfiguration

class FakeConnection:
    def cursor(self):
        return self
    def execute(self, query, args=None):
        return self
    def fetchall(self):
        return []
    def fetchone(self):
        return []
    def fetchmany(self, *args, **kwargs):
        return []
    def close(self):
        pass
    
class FakeQuerier(MaayQuerier):
    def __init__(self, *args, **kwargs):
        self._cnx = FakeConnection()

class FakeChecker:
    implements(ICredentialsChecker)
    credentialInterfaces = (IUsernamePassword,)

    def __init__(self, realm):
        self.realm = realm
        
    def requestAvatarId(self, creds):
        # FakeChecker always succeeds
        self.realm.createUserSession(creds.username, FakeQuerier())
        return defer.succeed(creds.username)

# override default make_uid to have a predictible behaviour
rpc.make_uid = lambda username, password: username+password

class RPCServerTC(unittest.TestCase):
    def setUp(self):
        portal = MaayPortal(WebappConfiguration())
        portal.registerChecker(FakeChecker(portal.realm))
        self.portal = portal
        rpcserver = server.Site(rpc.MaayRPCServer(None, portal))
        self.p = reactor.listenTCP(0, rpcserver, interface="127.0.0.1")
        self.port = self.p.getHost().port
        
    def tearDown(self):
        self.p.stopListening()
        reactor.iterate()
        reactor.iterate()

    def _callRemote(self, methName, *args):
        proxy = xmlrpc.Proxy('http://localhost:%s' % self.port)
        return proxy.callRemote(methName, *args)        
    
    def testAnonymousAuthentication(self):
        self.portal.anonymousQuerier = object() # could be anything but None
        digest = self._callRemote('authenticate', '', '')
        got, _ = unittest.deferredResult(digest)
        self.assertEquals(_, '')
        self.assertEquals(got, ANONYMOUS_AVATARID)

    def testAnonymousAuthenticationFailure(self):
        """when portal.anonymousQuerier is None, anonymous login is not allowed"""
        self.portal.anonymousQuerier = None
        digest = self._callRemote('authenticate', '', '')
        got, err = unittest.deferredResult(digest)
        self.assertEquals(got, '')
        # XXX: need a better check
        self.assertNotEquals(err, '')
        

    def testRawAuthentication(self):
        for user, passwd in [('adim', 'adim'), ('foo', 'bar')]:
            digest = self._callRemote('authenticate', user, passwd)
            expected = rpc.make_uid(user, passwd)
            got, _ = unittest.deferredResult(digest)
            self.assertEquals(got, expected, ('%s != %s (%s)' % (got, expected, _)))
            self.assertEquals(_, '')
    
    def testUncertifiedRemoteCall(self):
        """only authentified people should be able to call remote methods"""
        retValue = self._callRemote('lastIndexationTimeAndState', 'evil', 'foo.pdf')
        self.assertEquals(unittest.deferredResult(retValue), [-1, Document.UNKNOWN_STATE])

    def testCertifiedRemoteCall(self):
        d = self._callRemote('authenticate', 'adim', 'adim')
        cnxId, _ = unittest.deferredResult(d)
        retValue = self._callRemote('lastIndexationTimeAndState', cnxId, 'foo.pdf')
        self.assertEquals(unittest.deferredResult(retValue), [0, Document.UNKNOWN_STATE])

if __name__ == '__main__':
    # FIXME: the following is nicer but triggers an assertion
    #        because we imported twisted.internet.reactor
##     from  twisted.scripts.trial import run
##     run()
    import sys
    import os
    os.system('trial %s'%sys.argv[0])
