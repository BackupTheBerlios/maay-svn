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

from maay import rpc
from maay.querier import MaayQuerier
from maay.server import MaayPortal, WebappConfiguration

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
        rpcserver = server.Site(rpc.MaayRPCServer(portal))
        self.p = reactor.listenTCP(0, rpcserver, interface="127.0.0.1")
        self.port = self.p.getHost().port
        
    def tearDown(self):
        self.p.stopListening()
        reactor.iterate()
        reactor.iterate()

    def _callRemote(self, methName, *args):
        proxy = xmlrpc.Proxy('http://localhost:%s' % self.port)
        return proxy.callRemote(methName, *args)        
    
    def testRawAuthentication(self):
        for user, passwd in [('adim', 'adim'), ('foo', 'bar')]:
            digest = self._callRemote('authenticate', user, passwd)
            expected = rpc.make_uid(user, passwd)
            self.assertEquals(unittest.deferredResult(digest), expected)

    def testUncertifiedRemoteCall(self):
        """only authentified people should be able to call remote methods"""
        retValue = self._callRemote('lastIndexationTime', 'evil', 'foo.pdf')
        self.assertEquals(unittest.deferredResult(retValue), -1)

    def testCertifiedRemoteCall(self):
        d = self._callRemote('authenticate', 'adim', 'adim')
        cnxId = unittest.deferredResult(d)
        retValue = self._callRemote('lastIndexationTime', cnxId, 'foo.pdf')
        self.assertEquals(unittest.deferredResult(retValue), 0)

if __name__ == '__main__':
    # FIXME: the following is nicer but triggers an assertion
    #        because we imported twisted.internet.reactor
##     from  twisted.scripts.trial import run
##     run()
    import sys
    import os
    os.system('trial %s'%sys.argv[0])
