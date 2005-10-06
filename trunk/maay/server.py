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

from zope.interface import implements

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
# this is to help py2exe
import nevow.flat.flatstan
import nevow.query
import twisted.web.woven.guard
import MySQLdb

from logilab.common.textutils import normalize_text

from maay.querier import MaayQuerier, IQuerier, AnonymousQuerier, \
     MaayAuthenticationError, ANONYMOUS_AVATARID
from maay.rpc import MaayRPCServer
from maay.configuration import get_path_of, Configuration
from maay.texttool import makeAbstract, WORDS_RGX, normalizeText


class MaayPage(rend.Page):
    child_maaycss = static.File(get_path_of('maay.css'))
    child_images = static.File(get_path_of('images/'))

    def __init__(self, maayId):
        rend.Page.__init__(self)
        self.maayId = maayId

    def render_loginurl(self, context, data):
        if self.maayId != ANONYMOUS_AVATARID:
            context.fillSlots('actionlabel', 'Logout')
            context.fillSlots('loginurl', '/logout')
        else:
            context.fillSlots('actionlabel', 'Login')            
            context.fillSlots('loginurl', '/login')
        return context.tag

    def child_login(self, context):
        return LoginForm(self.maayId)

    def child_logout(self, context):
        print "sure we're not here ?"
        req = inevow.IRequest(context)
        req.getSession().expire()
        req.redirect('/' + guard.LOGOUT_AVATAR)


class LoginForm(MaayPage):
    """a basic login form. This page is rendered until the user
    is logged.
    """
    addSlash = True
    docFactory = loaders.stan(
        tags.html[
            tags.head[tags.title["Maay Login Page",],
                      tags.link(rel='stylesheet', type='text/css', href='maaycss'),
                      tags.link(rel='shortcut icon', href='images/maay.ico'),
                      ],
            
            tags.body[
                tags.form(action='/'+guard.LOGIN_AVATAR, method='post')[
                    tags.table(_class="loginTable")[
                        tags.tr[
                            tags.td[ "Username:" ],
                            tags.td[ tags.input(type='text', name='username') ],
                            ],
                        tags.tr[
                            tags.td[ "Password:" ],
                            tags.td[ tags.input(type='password', name='password') ],
                            ]
                        ],
                    tags.input(type='submit'),
                    tags.p,
                    ]
                ]
            ]
        )


def normalizeMimetype(fileExtension):
    import mimetypes
    return mimetypes.types_map.get('.%s' % fileExtension)

class Query(object):
    restrictions = ('filetype', 'filename')

    def __init__(self, words, offset=0, filetype=None, filename=None):
        self.words = words # unicode string 
        self.offset = offset
        self.filetype = normalizeMimetype(filetype)
        self.filename = filename

    def fromRawQuery(rawQuery, offset=0):
        rawWords = rawQuery.split()
        words = []
        restrictions = {}
        for word in rawWords:
            try:
                restType, restValue = [s.strip() for s in word.split(':')]
            except ValueError:
                words.append(word)
            else:
                if restType in Query.restrictions:
                    # Python does not support unicode keywords !
                    # (note: restType is pure ASCII, so no pb with str())
                    restrictions[str(restType)] = restValue
                else:
                    words.append(word)
        return Query(u' '.join(words), offset, **restrictions)
    fromRawQuery = staticmethod(fromRawQuery)

    def __repr__(self):
        return 'Query Object (%s, %s, %s)' % (self.words, self.filetype,
                                              self.filename)

class SearchForm(MaayPage):
    """default search form"""
    docFactory = loaders.xmlfile(get_path_of('searchform.html'))
    addSlash = True

    def __init__(self, maayId, querier):
        MaayPage.__init__(self, maayId)
        self.querier = querier

    def logout(self):
        print "Bye %s !" % (self.maayId,)
        # XXX: logout message should be forwarded to registration server
        return None

    def child_search(self, context):
        # query = unicode(context.arg('words'))
        offset = int(context.arg('offset', 0))
        query = Query.fromRawQuery(unicode(context.arg('words')), offset)
        results = self.querier.findDocuments(query)
        return ResultsPage(self.maayId, results, query)

    # XXX make sure that the requested document is really in the database
    # XXX don't forget to update the download statistics of the document
    def child_download(self, context):
        docid = context.arg('docid')
        # query = unicode(context.arg('words'))
        query = Query.fromRawQuery(unicode(context.arg('words')))
        docurl = self.querier.notifyDownload(docid, query.words)
        if docurl:
            return static.File(docurl)
        else:
            return Maay404()


class ResultsPage(MaayPage):
    """default results page"""
    docFactory = loaders.xmlfile(get_path_of('resultpage.html'))
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

    def render_prevset_url(self, context, data):
        words = WORDS_RGX.findall(normalizeText(unicode(context.arg('words'))))
        offset = int(context.arg('offset', 0))
        if offset:
            offset -= 15
        return 'search?words=%s&offset=%s' % ('+'.join(words), offset)

    def render_nextset_url(self, context, data):
        words = WORDS_RGX.findall(normalizeText(unicode(context.arg('words'))))
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
                    print "Building search form with", avatarId
                    resc = SearchForm(avatarId, querier)
                return inevow.IResource, resc, resc.logout
            # if we wera asked for a querier
            elif iface is IQuerier:
                querier = self._getQuerier(avatarId)
                if querier is None:
                    return IQuerier, None, lambda: None
                else:
                    return IQuerier, querier, querier.close
                
    def _getQuerier(self, avatarId):
        try:
            querier = self._sessions[avatarId]
            print "Hit cache !"
        except KeyError:
            print "Ouch ! What am I supposed to do ?!!"
            querier = None
        return querier


class MaayPortal(portal.Portal):
    """Portal for Maay authentication system"""
    def __init__(self, webappConfig):
        realm = MaayRealm()
        checker = DBAuthChecker(realm, webappConfig.db_host,
                                webappConfig.db_name)
        portal.Portal.__init__(self, realm, (checker,))
        self.registerChecker(MaayAnonymousChecker(), IAnonymous)
        self.config = webappConfig
        # Create default anonymous querier, based on local configuration
        try:
            anonymousQuerier = AnonymousQuerier(host=webappConfig.db_host,
                                                database=webappConfig.db_name,
                                                user=webappConfig.user,
                                                password=webappConfig.password)
        except Exception, exc:
            # unable to create an anonymous querier
            print "***"
            print "*** Could not create anonymous querier"
            print "*** Got exception", exc
            print "*** This will disable the P2P functionalities"
            print "*** and force the user to login for local search"
            print "***"
            anonymousQuerier = None
        else:
            realm.createUserSession(ANONYMOUS_AVATARID, anonymousQuerier)
            anonymousQuerier.registerNode(self.config.get_node_id(),
                                          ip=socket.gethostbyname(socket.gethostname()),
                                          port=6789, bandwidth=10)
        self.anonymousQuerier = anonymousQuerier

class MaayAnonymousChecker(AllowAnonymousAccess):
    """don't use default twisted.cred anonymous avatarId"""
    def requestAvatarId(self, credentials):
        return ANONYMOUS_AVATARID


class DBAuthChecker:
    """user authentication checker
    cf. twisted's CRED system for more details
    """
    implements(ICredentialsChecker)
    credentialInterfaces = (IUsernamePassword,)
    
    def __init__(self, realm, dbhost, dbname):
        self.realm = realm
        self.dbhost = dbhost
        self.dbname = dbname
    
    def requestAvatarId(self, creds):
        try:
            querier = MaayQuerier(host=self.dbhost, database=self.dbname,
                                  user=creds.username, password=creds.password)
        except MaayAuthenticationError:
            print "Got Authentication Error !"
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
                filename = os.path.join(directory,'node_id')
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
                filename = os.path.join(directory, 'node_id')
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
                
    

    
def run():
    webappConfig = WebappConfiguration()
    webappConfig.load()
    maayPortal = MaayPortal(webappConfig)
    website = appserver.NevowSite(guard.SessionWrapper(maayPortal,
                                                       mindFactory=MaayMindFactory))
    website.remember(Maay404(), inevow.ICanHandleNotFound)
    rpcserver = server.Site(MaayRPCServer(maayPortal))
    reactor.listenTCP(8080, website)
    reactor.listenTCP(6789, rpcserver)
    print "Go !"
    reactor.run()

if __name__ == '__main__':
    run()
