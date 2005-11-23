#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Maay Node

The node is reponsible for running the web user interface and
an xmlrpc server for the indexer and distributed queries.
"""

__revision__ = '$Id$'

from maay.nodeconfig import nodeConfig

import platform
import sha
import time
import os
import socket
import sys

from zope.interface import implements

from twisted.cred import portal, error
from twisted.cred.checkers import AllowAnonymousAccess, \
     ICredentialsChecker
from twisted.cred.credentials import IAnonymous, IUsernamePassword
from twisted.internet import reactor, defer
from twisted.web import server
from twisted.python import failure
from nevow import inevow, appserver, guard
from twisted.python import log

# These imports are not used, but they help py2exe tremendously.
# Do not remove them (that is, unless we change the database backend
# or drop twisted)
import nevow.flat.flatstan
import nevow.query
import nevow.i18n
import nevow.flat.flatmdom
import MySQLdb
# end of py2exe helping imports

from maay.querier import MaayQuerier, IQuerier, AnonymousQuerier, \
     MaayAuthenticationError, WEB_AVATARID
from maay.rpc import MaayRPCServer

from maay import presenceclient
from maay.webapplication import Maay404, INodeConfiguration, SearchForm


## nevow app/server setup ############################################

NODE_HOST = socket.gethostbyname(socket.gethostname())
NODE_PORT = nodeConfig.rpcserver_port


# MaayMindFactory might be helpful to access request informations
# in portal. (not sure it's really aimed to be used this way :-)
class MaayMindFactory:
    def __init__(self, request, credentials):
        pass

class MaayRealm:
    """simple realm for Maay application"""
    implements(portal.IRealm)

    def __init__(self):
        self._sessions = {}

    def createUserSession(self, avatarId, querier):
        """associate a querier to an avatarId.
        Use avatarId=None for the internal private database connection"""
        print "MaayRealm : creating session for avatar", avatarId,
        print "with a", type(querier), "querier."
        self._sessions[avatarId] = querier

    def requestAvatar(self, avatarId, mind, *interfaces):
        """Our realm provides 2 different kinds of avatars :
          - HTML resources (for web applications)
          - queriers (for XMLRPC queries)

        Both kind of avatars rely on a querier instance
        """
        print "MaayRealm requestAvatar %s" % avatarId
        for iface in interfaces:
            # if we were asked for a web resource
            if iface is inevow.IResource:
                querier = self._getQuerier(avatarId)
                assert(MaayRPCServer.theP2pQuerier is not None)
                resc = SearchForm(avatarId, querier, MaayRPCServer.theP2pQuerier)
                return inevow.IResource, resc, resc.logout
            # if we were asked for a querier
            elif iface is IQuerier:
                querier = self._getQuerier(avatarId)
                if querier is None:
                    return IQuerier, None, lambda: None
                else:
                    return IQuerier, querier, querier.close
                
    def _getQuerier(self, avatarId):
        try:
            querier = self._sessions[avatarId]
            print "MaayRealm : querier of type", type(querier), "for avatar",
            print avatarId, "was in the session cache."
        except KeyError:
            print "MaayRealm : no querier in cache for", str(avatarId)+ \
                  ". What are we supposed to do ?"
            querier = None
        return querier


class MaayPortal(object, portal.Portal):
    """Portal for Maay authentication system"""
    def __init__(self, nodeConfig):
        print "Portal creation"
        realm = MaayRealm()
        checker = DBAuthChecker(realm, nodeConfig.db_host,
                                nodeConfig.db_name)
        portal.Portal.__init__(self, realm, (checker,))
        self.anonymousChecker = MaayAnonymousChecker()
        self.registerChecker(self.anonymousChecker, IAnonymous)
        self.config = nodeConfig
        # Create default web querier, based on local configuration
        try:
            print "Credentials : "
            print "  - host", nodeConfig.db_host
            print "  - db", nodeConfig.db_name
            print "  - user", nodeConfig.user
            print "  - pass", nodeConfig.password
            webQuerier = MaayQuerier(host=nodeConfig.db_host,
                                     database=nodeConfig.db_name,
                                     user=nodeConfig.user,
                                     password=nodeConfig.password)
        except Exception, exc:
            # unable to create a web querier
            print "***"
            print "*** Could not create web querier"
            print "*** Got exception", exc
            print "*** This may hurt in unexpected ways"
            print "***"
            webQuerier = None
        else:
            realm.createUserSession(WEB_AVATARID, webQuerier)
            webQuerier.registerNode(self.config.get_node_id(),
                                    ip=NODE_HOST,
                                    port=NODE_PORT,
                                    bandwidth=nodeConfig.bandwidth)
        self.webQuerier = webQuerier
        self.anonymousQuerier = AnonymousQuerier(host=nodeConfig.db_host,
                                                 database=nodeConfig.db_name,
                                                 user=nodeConfig.user,
                                                 password=nodeConfig.password)


    def getWebQuerier(self):
        return getattr(self, '_webQuerier', None)

    def setWebQuerier(self, value):
        """used to set 'anonymousAllowed' flag in anonymous checker"""
        #XXX: now, check this seriously
        if value is not None:
            self.anonymousChecker.anonymousAllowed = True
        self._webQuerier = value

    webQuerier = property(getWebQuerier, setWebQuerier,
                          doc="web querier")


class MaayAnonymousChecker(AllowAnonymousAccess):
    """don't use default twisted.cred anonymous avatarId"""
    def __init__(self):
        self.anonymousAllowed = False
        
    def requestAvatarId(self, credentials):
        print "AnonymousChecker : requestAvatarId", credentials
        if self.anonymousAllowed:
            return WEB_AVATARID #XXX: FIXME
        else:
            return failure.Failure(error.UnauthorizedLogin(
                "No anonymous querier available !"))


class DBAuthChecker:
    """user authentication checker
    cf. twisted's CRED system for more details
    """
    implements(ICredentialsChecker)
    credentialInterfaces = (IUsernamePassword,)
    
    def __init__(self, realm, dbhost, dbname):
        print "DBAuthChecker inits in realm", realm, "dbhost", dbhost,
        print "and dbname", str(dbname)+"."
        self.realm = realm
        self.dbhost = dbhost
        self.dbname = dbname
        self.querierCache = {}
    
    def requestAvatarId(self, creds):
        print "DBAuthChecker : checking credentials for DB access"
        try:
            querier = self.querierCache[(creds.username, creds.password)]
            print " querier was in the cache for",
        except KeyError:
            print " no querier in cache for",
            try:
                querier = MaayQuerier(host=self.dbhost, database=self.dbname,
                                      user=creds.username,
                                      password=creds.password)
                self.querierCache[(creds.username, creds.password)] = querier
            except MaayAuthenticationError:
                print ; print "DBAuthChecker : Authentication Error"
                return failure.Failure(error.UnauthorizedLogin())
        print creds.username
        self.realm.createUserSession(creds.username, querier)
        return defer.succeed(creds.username)


class MaaySessionWrapper(guard.SessionWrapper):
    """override guard.SessionWrapper to add an explicit errBack on
    portal.login()

    XXX: TODO check if we could not use SessionWrapper.incorrectLoginError()
    """
    def login(self, request, session, credentials, segments):
        # d = SessionWrapper.login()
        # d.addErrback(..)
        print "MaaySessionWrapper login", credentials, session, request, segments
        mind = self.mindFactory(request, credentials)
        session.mind = mind
        d = self.portal.login(credentials, mind, self.credInterface)
        d.addCallback(self._cbLoginSuccess, session, segments)
        #d.addErrback(self._forceLoginPage)
        return d

##     def _forceLoginPage(self, *args):
##         return LoginForm(), ''

    
def run():
    log.startLogging(open('maay-node.log', 'w'))
    maayPortal = MaayPortal(nodeConfig)
    website = appserver.NevowSite(MaaySessionWrapper(maayPortal,
                                                     mindFactory=MaayMindFactory))
    website.remember(Maay404(), inevow.ICanHandleNotFound)
    website.remember(nodeConfig, INodeConfiguration)
    presenceclient.notify(nodeConfig.presence_host,
                          nodeConfig.presence_port,
                          maayPortal.webQuerier,
                          nodeConfig.get_node_id(),
                          socket.gethostbyname(socket.gethostname()),
                          nodeConfig.rpcserver_port,
                          nodeConfig.bandwidth)
    
    rpcserver = server.Site(MaayRPCServer(maayPortal))
    reactor.listenTCP(nodeConfig.webserver_port, website)
    reactor.listenTCP(nodeConfig.rpcserver_port, rpcserver)
    try:
        try:
            print "-------------Starting Node mainloop-------------"
            reactor.run()
        except ValueError:
            # Note: twisted raise an error if reactor is not run in the
            # main thread. This occurs when maay is runned as a windows
            # service.
            if sys.platform == 'win32':
                reactor.run(installSignalHandlers=0)
            else:
                raise
    finally:
        print "---------------Shutting down Node---------------"


if __name__ == '__main__':
    run()
