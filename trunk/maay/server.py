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

from datetime import datetime
import warnings
warnings.filterwarnings("ignore", ".*", DeprecationWarning, "nevow.static")
warnings.filterwarnings("ignore", ".*", DeprecationWarning, "twisted.python.reflect")
warnings.filterwarnings("ignore", ".*", DeprecationWarning, "twisted.web.woven")

import platform
import sha
import time
import os
import re
import socket

from zope.interface import implements, Interface

from twisted.cred import portal, checkers, error
from twisted.cred.checkers import ANONYMOUS, AllowAnonymousAccess, \
     ICredentialsChecker
from twisted.cred.credentials import IAnonymous, IUsernamePassword
from twisted.internet import reactor, defer
from twisted.web import server
from twisted.web import static
from twisted.python import failure

from nevow import inevow, rend, tags, guard, loaders, appserver
from nevow.url import URL

# These imports are not used, but they help py2exe tremendously.
# Do not remove them (that is, unless we change the database backend
# or drop twisted)
import nevow.flat.flatstan
import nevow.query
import twisted.web.woven.guard
import MySQLdb
# end of py2exe helping imports

from logilab.common.textutils import normalize_text

from maay.querier import MaayQuerier, IQuerier, \
     MaayAuthenticationError, ANONYMOUS_AVATARID
from maay.rpc import MaayRPCServer
from maay.configuration import get_path_of, Configuration
from maay.texttool import makeAbstract, WORDS_RGX, normalizeText
from maay import registrationclient
from maay.query import Query

ANONYMOUS_AVATARID = 'maay' # it's only a matter of definition after all ...

class MaayPage(rend.Page):
    docFactory = loaders.xmlfile(get_path_of('skeleton.html'))
    child_maaycss = static.File(get_path_of('maay.css'))
    child_images = static.File(get_path_of('images/'))

    def __init__(self, maayId=ANONYMOUS_AVATARID):
        rend.Page.__init__(self)
        self.maayId = maayId

#     def render_loginurl(self, context, data):
#         url = URL.fromContext(context)
#         store current URL into  'goThereAfter' to be able to return here
#         after login
#         goThereAfter = URL(url.scheme, url.netloc, url.pathList())
#         if self.maayId != ANONYMOUS_AVATARID:
#            goThereAfter = URL(url.scheme, url.netloc,
#                               ['logout'] + url.pathList())
#            context.fillSlots('actionlabel', 'Logout')
#         else:
#            goThereAfter = URL(url.scheme, url.netloc,
#                               ['login'] + url.pathList())
#            context.fillSlots('actionlabel', 'Login')            
#         for param, value in url.queryList():
#            goThereAfter = goThereAfter.add(param, value)
#         context.fillSlots('loginurl', str(goThereAfter))
#         return context.tag

    def macro_body(self, context):
        return self.bodyFactory

    def child_login(self, context):
        return LoginForm(self.maayId)

    def child_logout(self, context):
        print "sure we're not here ?"
        req = inevow.IRequest(context)
        req.getSession().expire()
        req.redirect('/' + guard.LOGOUT_AVATAR)

# class LoginForm(MaayPage):
#     """a basic login form. This page is rendered until the user
#     is logged.
#     """
#     # addSlash = True

#     def path(self, context, data):
#         here = URL.fromContext(context)
#         # transform /login/somePathAndQuery into /__login__/somePathAndQuery
#         # to benefit from nevow.guard redirection magic
#         pathList = ['__login__'] + here.pathList()[1:]
#         goThereAfter = URL(here.scheme, here.netloc,
#                            pathList, here.queryList())
#         return str(goThereAfter)

#     bodyFactory = loaders.stan(
#         tags.html[
#             tags.head[tags.title["Maay Login Page",],
#                       tags.link(rel='stylesheet', type='text/css', href='maay.css'),
#                       tags.link(rel='shortcut icon', href='images/maay.ico'),
#                       ],
            
#             tags.body[
#                 # tags.form(action='/'+guard.LOGIN_AVATAR, render=path, method='post')[
#                 tags.form(action=path, method='post')[
#                     tags.table(_class="loginTable")[
#                         tags.tr[
#                             tags.td[ "Username :" ],
#                             tags.td[ tags.input(type='text', name='username') ],
#                             ],
#                         tags.tr[
#                             tags.td[ "Password :" ],
#                             tags.td[ tags.input(type='password', name='password') ],
#                             ]
#                         ],
#                     tags.input(type='submit'),
#                     tags.p,
#                     ]
#                 ]
#             ]
#         )

#     def childFactory(self, context, segments):
#         print " child factory"
#         return LoginForm()

class PeersList(MaayPage):
    """display list of registered peers"""
    bodyFactory = loaders.xmlfile(get_path_of('peers.html'))
    addSlash = True

    def __init__(self, maayId, querier):
        MaayPage.__init__(self, maayId)
        self.querier = querier

    def data_peers(self, context, data):
        webappConfig = IWebappConfiguration(context)
        peers = self.querier.getActiveNeighbors(webappConfig.get_node_id(), 10)
        return peers
    
    def render_peer(self, context, peerNode):
        # Note: might be convenient to register a special flattener for
        #       Node objects
        for attrname in ('node_id', 'ip', 'port', 'last_seen_time',
                         'claim_count', 'affinity', 'bandwidth'):
            context.fillSlots(attrname, getattr(peerNode, attrname, 'N/A'))
        return context.tag
                    
class SearchForm(MaayPage):
    """default search form"""
    bodyFactory = loaders.xmlfile(get_path_of('searchform.html'))
    addSlash = True

    def __init__(self, maayId, querier):
        MaayPage.__init__(self, maayId)
        self.querier = querier

    def logout(self):
        print "Bye %s !" % (self.maayId,)
        # XXX: logout message should be forwarded to registration server
        return None

    def child_peers(self, context):
        return PeersList(self.maayId, self.querier)

    def child_search(self, context):
        # query = unicode(context.arg('words'))        
        offset = int(context.arg('offset', 0))
        query = Query.fromRawQuery(unicode(context.arg('words'), 'utf-8'), offset)
        results = self.querier.findDocuments(query)
        return ResultsPage(self.maayId, results, query)

    # XXX make sure that the requested document is really in the database
    # XXX don't forget to update the download statistics of the document
    def child_download(self, context):
        docid = context.arg('docid')
        # query = unicode(context.arg('words'))
        query = Query.fromRawQuery(unicode(context.arg('words'), 'utf-8'))
        docurl = self.querier.notifyDownload(docid, query.words)
        if docurl:
            return static.File(docurl)
        else:
            return Maay404()


class ResultsPage(MaayPage):
    """default results page"""
    bodyFactory = loaders.xmlfile(get_path_of('resultpage.html'))
    addSlash = False
    
    def __init__(self, maayId, results, query):
        MaayPage.__init__(self, maayId)
        self.results = results
        self.query = query.words # unicode(query)

    def data_results(self, context, data):
        return self.results

    def render_title(self, context, data):
        context.fillSlots('words', self.query)
        return context.tag

    def render_searchfield(self, context, data):
        context.fillSlots('words', self.query)
        return context.tag

    def render_prevset_url(self, context, data):
        words = WORDS_RGX.findall(normalizeText(unicode(context.arg('words'), 'utf-8')))
        offset = int(context.arg('offset', 0))
        if offset:
            offset -= 15
        return 'search?words=%s&offset=%s' % ('+'.join(words), offset)

    def render_nextset_url(self, context, data):
        words = WORDS_RGX.findall(normalizeText(unicode(context.arg('words'), 'utf-8')))
        offset = int(context.arg('offset', 0)) + 15
        return 'search?words=%s&offset=%s' % ('+'.join(words), offset)

    
    def render_row(self, context, data):
        document = data
        context.fillSlots('doctitle',  document.title)
        # XXX abstract attribute should be a unicode string
        try:
            abstract = makeAbstract(document.text, self.query.split())
            abstract = normalize_text(unicode(abstract))
        except Exception, exc:
            print exc
            abstract = u'No abstract available for this document [%s]' % exc
        context.fillSlots('abstract', tags.xml(abstract))
        context.fillSlots('docid', document.db_document_id)
        context.fillSlots('docurl', document.url)
        context.fillSlots('words', self.query)
        context.fillSlots('readable_size', document.readable_size())
        date = datetime.fromtimestamp(document.publication_time)
        context.fillSlots('publication_date', date.strftime('%d/%m/%Y'))
        return context.tag

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
        print "Maay Realm : creating session for avatar", avatarId,
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
            # if we wer asked for a querier
            elif iface is IQuerier:
                querier = self._getQuerier(avatarId)
                if querier is None:
                    return IQuerier, None, lambda: None
                else:
                    return IQuerier, querier, querier.close
                
    def _getQuerier(self, avatarId):
        try:
            querier = self._sessions[avatarId]
            print "Querier of type", type(querier), "for avatar",
            print avatarId, "was in the cache. Good."
        except KeyError:
            print "No querier in cache for", str(avatarId)+ \
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
            realm.createUserSession(ANONYMOUS_AVATARID, webQuerier)
            webQuerier.registerNode(self.config.get_node_id(),
                                    ip=socket.gethostbyname(socket.gethostname()),
                                    port=webappConfig.rpcserver_port,
                                    bandwidth=webappConfig.bandwidth)
        self.webQuerier = webQuerier

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
        if self.anonymousAllowed:
            return ANONYMOUS_AVATARID
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
	# Keeping a cache of queriers reusing the same has some benefits :)
        self.querierCache = {}
    
    def requestAvatarId(self, creds):
        print "DBAuthChecker : checking credentials for DB access"
        try:
	    try:
		querier = self.querierCache[creds]
	    except KeyError:
		querier = MaayQuerier(host=self.dbhost, database=self.dbname,
				      user=creds.username,
				      password=creds.password)
		self.querierCache[creds] = querier
        except MaayAuthenticationError:
            print "DBAuthChecker : Authentication Error"
            return failure.Failure(error.UnauthorizedLogin())
        self.realm.createUserSession(creds.username, querier)
        return defer.succeed(creds.username)


class Maay404(rend.FourOhFour):
    """Maay specific resource for 404 errors"""
    loader = loaders.xmlfile(get_path_of('notfound.html'))

    def renderHTTP_notFound(self, context):
        """Render a not found message to the given request.
        """
        return self.loader.load(context)[0]

class IWebappConfiguration(Interface):
    """provide an interface in order to be able to remember webappconfig"""

class WebappConfiguration(Configuration):
    options = [
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
        for directory in self.get_config_dirs():
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
        for directory in self.get_config_dirs():
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
        mind = self.mindFactory(request, credentials)
        session.mind = mind
        d = self.portal.login(credentials, mind, self.credInterface)
        d.addCallback(self._cbLoginSuccess, session, segments)
        d.addErrback(self._forceLoginPage)
        return d

    def _forceLoginPage(self, *args):
        return LoginForm(), ''
    
    
def run():
    webappConfig = WebappConfiguration()
    webappConfig.load()
    maayPortal = MaayPortal(webappConfig)
    website = appserver.NevowSite(MaaySessionWrapper(maayPortal,
                                                     mindFactory=MaayMindFactory))
    website.remember(Maay404(), inevow.ICanHandleNotFound)
    website.remember(webappConfig, IWebappConfiguration)
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
    print "In the mainloop ..."
    reactor.run()

if __name__ == '__main__':
    run()
