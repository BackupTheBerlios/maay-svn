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

"""maay local web UI script"""

__revision__ = '$Id$'


import platform
import sha
import time
import os
import re
import socket

from zope.interface import implements

from twisted.cred import portal, error
from twisted.cred.checkers import AllowAnonymousAccess, \
     ICredentialsChecker
from twisted.cred.credentials import IAnonymous, IUsernamePassword
from twisted.internet import reactor, defer
from twisted.web import server
from twisted.python import failure
from nevow import inevow, appserver, guard

# These imports are not used, but they help py2exe tremendously.
# Do not remove them (that is, unless we change the database backend
# or drop twisted)
import nevow.flat.flatstan
import nevow.query
import twisted.web.woven.guard
import MySQLdb
# end of py2exe helping imports

from maay.querier import MaayQuerier, IQuerier, AnonymousQuerier, \
     MaayAuthenticationError, WEB_AVATARID
from maay.rpc import MaayRPCServer
from maay.configuration import Configuration
from maay import registrationclient
from maay.webapplication import Maay404, IServerConfiguration, SearchForm


## nevow app/server setup ############################################

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
        for iface in interfaces:
            # if we were asked for a web resource
            if iface is inevow.IResource:
                querier = self._getQuerier(avatarId)
                if querier is None:
                    return inevow.IResource, LoginForm(), lambda: None
                else:
                    print "Building search form for", avatarId
                    resc = SearchForm(avatarId, querier)
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
    def __init__(self, webappConfig):
        print "Portal creation"
        realm = MaayRealm()
        checker = DBAuthChecker(realm, webappConfig.db_host,
                                webappConfig.db_name)
        portal.Portal.__init__(self, realm, (checker,))
        self.anonymousChecker = MaayAnonymousChecker()
        self.registerChecker(self.anonymousChecker, IAnonymous)
        self.config = webappConfig
        # Create default web querier, based on local configuration
        try:
            print "Credentials : "
            print "  - host", webappConfig.db_host
            print "  - db", webappConfig.db_name
            print "  - user", webappConfig.user
            print "  - pass", webappConfig.password
            webQuerier = MaayQuerier(host=webappConfig.db_host,
                                     database=webappConfig.db_name,
                                     user=webappConfig.user,
                                     password=webappConfig.password)
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
                                    ip=socket.gethostbyname(socket.gethostname()),
                                    port=webappConfig.rpcserver_port,
                                    bandwidth=webappConfig.bandwidth)
        self.webQuerier = webQuerier
        self.anonymousQuerier = AnonymousQuerier(host=webappConfig.db_host,
                                                 database=webappConfig.db_name,
                                                 user=webappConfig.user,
                                                 password=webappConfig.password)


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




class ServerConfiguration(Configuration):
    options = Configuration.options + [
        ('db-name',
         {'type' : "string", 'metavar' : "<dbname>", 'short' : "d",
          'help' : "name of the Maay database",
          'default' : "maay",
          }),
        ('db-host',
         {'type' : "string", 'metavar' : "<dbhost>", 'short' : "H",
          'help' : "which server hosts the database",
          'default' : "localhost",
          }),
        ('user',
         {'type': 'string',
          'metavar': '<userid>', 'short': 'u',
          'help': 'login of anonymous user to use to connect to the database',
          'default' : "maay",
          }),
        ('password',
         {'type': 'string',
          'metavar': '<password>', 'short' : "p",
          'help': 'password of anonymous user to use to connect to the database',
          'default' : "maay",
          }),
        ('registration-host',
         {'type' : "string", 'metavar' : "<registration_host>", 
          'help' : "Host name or IP address of the registration server",
          'default' : "localhost",
          }),
        ('registration-port',
         {'type' : "int", 'metavar' : "<registration_port>", 
          'help' : "Internet port on which the registration server is listening",
          'default' : 2345,
          }),
        ('webserver-port',
         {'type' : "int", 'metavar' : "<webserver_port>", 
          'help' : "Internet port on which the web interface is listening",
          'default' : 7777,
          }),
        ('rpcserver-port',
         {'type' : "int", 'metavar' : "<rpcserver_port>", 
          'help' : "Internet port on which the xmlrpc server is listening",
          'default' : 6789,
          }),
        ('bandwidth',
         {'type' : "int", 'metavar' : "<bandwidth>", 
          'help' : "Internet port on which the xmlrpc server is listening",
          'default' : 10,
          }),
        ('nodeid-file',
         {'type' : "string", 'metavar' : "<node_id_file>",
          'help' : "Maay will store the generated node id in this file",
          'default' : "node_id",
          }),
        ]

    config_file = 'webapp.ini'

    def __init__(self):
        Configuration.__init__(self, name="Server")
        self.node_id = None

    def get_node_id(self):
        if not self.node_id:
            self.node_id = self._read_node_id()
        return self.node_id

    def _read_node_id(self):
        for directory in self.get_writable_config_dirs():
            try:
                filename = os.path.join(directory, self.nodeid_file)
                f = open(filename,'r')
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    node_id = line.strip()
                    assert re.match('^[0-9a-fA-F]{40}$', node_id)
                    f.close()
                    return node_id
            except IOError:
                continue
        self._write_node_id()
        return self._read_node_id()

    def _generate_node_id(self):
        hasher = sha.sha()
        hasher.update(''.join(platform.uname()))
        hasher.update('%s' % id(self))
        hasher.update('%s' % time.time())
        return hasher.hexdigest()

    def _write_node_id(self):
        node_id = self._generate_node_id()
        for directory in self.get_writable_config_dirs():
            try:
                filename = os.path.join(directory, self.nodeid_file)
                f = open(filename, 'w')
                lines = ['# This file contains the Node Identifier for your computer\n',
                         '# Do not edit it or erase it, or this will corrupt the database\n',
                         '# of your Maay instance.\n',
                         '# This id was generated on %s\n' % time.asctime(),
                         '%s\n' % node_id
                         ]
                f.writelines(lines)
                f.close()
                return
            except IOError:
                continue
        raise ValueError('Unable to find a writable directory to store the node id')


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

    def _forceLoginPage(self, *args):
        return LoginForm(), ''
    
    
def run():
    webappConfig = ServerConfiguration()
    webappConfig.load()
    maayPortal = MaayPortal(webappConfig)
    website = appserver.NevowSite(MaaySessionWrapper(maayPortal,
                                                     mindFactory=MaayMindFactory))
    website.remember(Maay404(), inevow.ICanHandleNotFound)
    website.remember(webappConfig, IServerConfiguration)
    registrationclient.login(reactor,
                             webappConfig.registration_host, webappConfig.registration_port,
                             maayPortal.webQuerier,
                             webappConfig.get_node_id(),
                             socket.gethostbyname(socket.gethostname()),
                             webappConfig.rpcserver_port,
                             webappConfig.bandwidth)
                                                  
                             
    rpcserver = server.Site(MaayRPCServer(webappConfig.get_node_id(),
                                          maayPortal))
    reactor.listenTCP(webappConfig.webserver_port, website)
    reactor.listenTCP(webappConfig.rpcserver_port, rpcserver)
    try:
        print "-------------Server mainloop-------------"
        reactor.run()
    finally:
        print "-----------Shutting down Server----------"
        
        registrationclient.logout(reactor,
                                  webappConfig.registration_host,
                                  webappConfig.registration_port,
                                  webappConfig.get_node_id())
        
        

if __name__ == '__main__':
    run()
