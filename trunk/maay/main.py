"""maay local web UI script"""

__revision__ = '$Id$'

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

from logilab.common.textutils import normalize_text

from maay.querier import MaayQuerier, IQuerier
from maay.rpc import MaayRPCServer
from maay.configuration import get_path_of, Configuration

class MaayPage(rend.Page):
    child_maaycss = static.File(get_path_of('maay.css'))
    child_images = static.File(get_path_of('images/'))
    

class LoginForm(MaayPage):
    """a basic login form. This page is rendered until the user
    is logged.
    """
    addSlash = True
    docFactory = loaders.stan(
        tags.html[
            tags.head[tags.title["Maay Login Page"]],
            tags.body[
                tags.form(action=guard.LOGIN_AVATAR, method='post')[
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
    

class SearchForm(MaayPage):
    """default search form"""
    docFactory = loaders.xmlfile(get_path_of('searchform.html'))
    addSlash = True

    def __init__(self, maayId, querier):
        rend.Page.__init__(self)
        self.maayId = maayId
        self.querier = querier

    def logout(self):
        print "Bye"
        # XXX: logout message should be forwarded to registration server
        return None

    def child_search(self, context):
        words = context.arg('words')
        if isinstance(words, basestring):
            words = (words,)
        results = self.querier.findDocuments(words)
        return ResultsPage(results)



class ResultsPage(MaayPage):
    """default results page"""
    docFactory = loaders.xmlfile(get_path_of('resultpage.html'))
    addSlash = False
    
    def __init__(self, results):
        MaayPage.__init__(self)
        self.results = results

    def data_results(self, context, data):
        return self.results
    
    def render_row(self, context, data):
        document = data
        context.fillSlots('doctitle',  document.title)
        context.fillSlots('abstract', normalize_text(document.abstract))
        context.fillSlots('docurl', document.url)
        context.fillSlots('readable_size', document.readable_size())
        return context.tag


## nevow app/server setup ############################################
class MaayRealm:
    """simple realm for Maay application"""
    implements(portal.IRealm)

    def __init__(self):
        self._sessions = {}

    def createUserSession(self, avatarId, querier):
        self._sessions[avatarId] = querier

    def requestAvatar(self, avatarId, mind, *interfaces):
        for iface in interfaces:
            if iface is inevow.IResource:
                if avatarId is ANONYMOUS:
                    resc = LoginForm()
                    return inevow.IResource, resc, lambda: None
                else:
                    querier = self._getQuerier(avatarId)
                    if querier is None:
                        return inevow.IResource, LoginForm(), lambda: None
                    else:
                        resc = SearchForm(avatarId, querier)
                        return inevow.IResource, resc, resc.logout
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
        self.registerChecker(AllowAnonymousAccess(), IAnonymous)
    

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
        print "REQUESTING AVATAR ID for %s/%s" % (creds.username, creds.password)
        try:
            querier = MaayQuerier(host=self.dbhost, database=self.dbname,
                                  user=creds.username, password=creds.password)
        except: # Find which exceptions are raised (MySQLdb.OperationalError)
            print "Got Authentication Error !"
            import traceback
            traceback.print_exc()
            return failure.Failure(error.UnauthorizedLogin())
        self.realm.createUserSession(creds.username, querier)
        return defer.succeed(creds.username)


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
        ]

    config_file = 'webapp.ini'

    
def run():
    webappConfig = WebappConfiguration()
    webappConfig.load()
    maayPortal = MaayPortal(webappConfig)
    website = appserver.NevowSite(guard.SessionWrapper(maayPortal))
    rpcserver = server.Site(MaayRPCServer(maayPortal))
    reactor.listenTCP(8080, website)
    reactor.listenTCP(6789, rpcserver)
    print "Go !"
    reactor.run()

if __name__ == '__main__':
    run()
