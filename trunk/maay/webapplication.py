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

__revision__ = '$Id: server.py 281 2005-11-03 11:00:56Z aurelienc $'

from datetime import datetime
import re
from xmlrpclib import ServerProxy
from itertools import cycle

from zope.interface import Interface
from twisted.web import static
from nevow import rend, tags, loaders

from logilab.common.textutils import normalize_text

from maay.querier import WEB_AVATARID
from maay.configuration import get_path_of
from maay.texttool import makeAbstract, WORDS_RGX, normalizeText, boldifyText
from maay.query import Query
from maay.p2pquerier import P2pQuerier, P2pQuery
from maay.dbentity import Document
import maay.indexer

class INodeConfiguration(Interface):
    """provide an interface in order to be able to remember webappconfig"""


class Maay404(rend.FourOhFour):
    """Maay specific resource for 404 errors"""
    loader = loaders.xmlfile(get_path_of('notfound.html'))

    def renderHTTP_notFound(self, context):
        """Render a not found message to the given request.
        """
        return self.loader.load(context)[0]

class MaayPage(rend.Page):
    docFactory = loaders.xmlfile(get_path_of('skeleton.html'))
    child_maaycss = static.File(get_path_of('maay.css'))
    child_images = static.File(get_path_of('images/'))

    def __init__(self, maayId=WEB_AVATARID):
        rend.Page.__init__(self)
        self.maayId = maayId

    def macro_body(self, context):
        return self.bodyFactory

    def macro_footer(self, context):
        return loaders.xmlfile(get_path_of('footer.html'))

class PeersList(MaayPage):
    """display list of registered peers"""
    bodyFactory = loaders.xmlfile(get_path_of('peers.html'))
    addSlash = True

    def __init__(self, maayId, querier):
        MaayPage.__init__(self, maayId)
        self.querier = querier

    def data_peers(self, context, data):
        webappConfig = INodeConfiguration(context)
        myNodeId = webappConfig.get_node_id()
        print "PeerList data_peers : my_node_id =", myNodeId
        peers = self.querier.getActiveNeighbors(myNodeId, 10)
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

    def __init__(self, maayId, querier, p2pquerier=None):
        MaayPage.__init__(self, maayId)
        self.querier = querier
        self.p2pquerier = p2pquerier

    def logout(self):
        print "Bye %s !" % (self.maayId,)
        # XXX: logout message should be forwarded to presence server
        return None

    def child_peers(self, context):
        return PeersList(self.maayId, self.querier)

    def child_indexation(self, context):
        start = int(context.arg('start', 0))
        if start == 0:
            if maay.indexer.running:
                msg = "Indexer running"
            else:
                msg = "Indexer not running"
        else:
            if maay.indexer.running:    
                msg = "Indexer already running"
            else:
                msg = "Indexer started"
                maay.indexer.start_as_thread()

        return IndexationPage(msg)

    def child_search(self, context):
        return FACTORY.clientFactory(context, self.querier, self.p2pquerier)
    
    # XXX make sure that the requested document is really in the database
    # XXX don't forget to update the download statistics of the document
    def child_download(self, context):
        docid = context.arg('docid')
        query = Query.fromRawQuery(unicode(context.arg('words'), 'utf-8'))
        docurl = self.querier.notifyDownload(docid, query.words)
        if docurl:
            return static.File(docurl)
        else:
            return Maay404()

    def child_distantfile(self, context):
        host = context.arg('host')
        port = context.arg('port')
        #XXX: we *must* be able to get the query words here
        #     for now we can't
        filepath = context.arg('filepath')
        docid = context.arg('docid')
        if not host or not port or not filepath:
            return Maay404()
        proxy = ServerProxy('http://%s:%s' % (host, port))
        try:
            fileData = proxy.downloadFile(docid).data
        except:
            print "there was nothing to return, unfortunately ... try later ?"
            return
        return DistantFilePage(filepath, fileData)

class DistantFilePage(static.File):
    def __init__(self, filepath, fileContent):
        static.File.__init__(self, filepath)
        self.fileContent = fileContent
        
    def openForReading(self):
        from cStringIO import StringIO
        return StringIO(self.fileContent)

class IndexationPage(MaayPage):
    # just for the demo. Should be moved to a adminpanel interface later.
    """index page"""
    bodyFactory = loaders.xmlfile(get_path_of('indexationpage.html'))
    addSlash = False
    
    def __init__(self, msg = "No message"):
        MaayPage.__init__(self)
        self._msg = msg

    def render_message(self, context, data):
        return self._msg

class ResultsPageMixIn:
            
    def data_results(self, context, data):
        return self.results
    
    def macro_footer(self, context):
        return loaders.xmlfile(get_path_of('footer.html'))

    def render_title(self, context, data):
        context.fillSlots('words', self.query.words)
        context.fillSlots('start_result', min(len(self.results), self.offset + 1))
        context.fillSlots('end_result', self.offset + len(self.results))
        return context.tag

    def render_searchfield(self, context, data):
        context.fillSlots('words', self.query.words)
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
        words = self.query.words.split()
        context.fillSlots('mime_type', re.sub("/", "_", document.mime_type))
        context.fillSlots('doctitle',
                          tags.xml(boldifyText(document.title, words)))
        # XXX abstract attribute should be a unicode string
        try:
            abstract = makeAbstract(document.text, words)
            abstract = normalize_text(unicode(abstract))
        except Exception, exc:
            import traceback
            traceback.print_exc()
            print exc
            abstract = u'No abstract available for this document [%s]' % exc
        context.fillSlots('abstract', tags.xml(abstract))
        context.fillSlots('docid', document.db_document_id)
        context.fillSlots('docurl', tags.xml(boldifyText(document.url, words)))
        context.fillSlots('words', self.query.words)
        context.fillSlots('readable_size', document.readable_size())
        date = datetime.fromtimestamp(document.publication_time)
        context.fillSlots('publication_date', date.strftime('%d %b %Y'))
        return context.tag
    
class StaticResultsPage(MaayPage, ResultsPageMixIn):
    bodyFactory = loaders.xmlfile(get_path_of('resultpage.html'))

    def __init__(self, results):
        self.results = results

from nevow import athena, inevow
from twisted.python import log

class ResultsPage(athena.LivePage, ResultsPageMixIn):
    """default results page"""
    child_maaycss = static.File(get_path_of('maay.css'))
    child_images = static.File(get_path_of('images/'))
    docFactory = loaders.xmlfile(get_path_of('liveresults.html'))
    addSlash = False

    def __init__(self, context, querier, p2pquerier):
        athena.LivePage.__init__(self)
        # XXX: nevow/livepage related trick (version 0.6.0) :
        # This resource is instanciated several times when rendering the
        # results page (each time the browser tries to load
        # ROOT/search/athena.js, ROOT/search/MochiKit.js, etc.) because
        # the Livepage-Id is not yet set in the request. In these particuliar
        # cases, we don't want to start new queries, so we do an ugly check
        # to test whether or not we're instanciating the *real* live page
        # (or if we're just trying to download JS files)
        # NOTE: At the time this comment is written, athena/LivePages are handled
        #       differently in nevow SVN. It's now possible to insantiate directly
        #       LivePage instances (which is great !), so we'll have to change
        #       the implementation for next nevow release.
        # NOTE2: another way to be sure that only the appopriate resource
        #        starts the p2pquery (and registers callbacks) would be
        #        to launch the query in the remote_conect() method
        if len(inevow.IRemainingSegments(context)) < 2:
            self.query = Query.fromContext(context)
            self.offset = self.query.offset
            #TODO: very soon, the line below will also be the p2pquerier's job
            self.results = querier.findDocuments(self.query)
            webappConfig = INodeConfiguration(context)
            p2pQuery = P2pQuery(webappConfig.get_node_id(),
                                webappConfig.rpcserver_port,
                                self.query)
            p2pquerier.sendQuery(p2pQuery)
            p2pquerier.addAnswerCallback(p2pQuery.qid, self.onNewResults)
            self.queryId = p2pQuery.qid
            self.querier = querier
            
    def onNewResults(self, provider, results):
        results = [Document(**params) for params in results]
        self.querier.pushDocuments(self.queryId, results, provider)
        results = self.querier.getQueryResults(self.queryId) # XXX offset, limit ?
        page = PleaseCloseYourEyes(results, provider, self.query, self.queryId).renderSynchronously()
        self.callRemote('updateResults', u'<div>%s</div>' % page)

    def remote_connect(self, context):
        """just here to start the connection between client and server (Ajax)"""
        self.querier.pushDocuments(self.queryId, self.results, provider=None)
        return 0


class PleaseCloseYourEyes(rend.Page, ResultsPageMixIn):
    """This resource and the way it is called is kind of ugly.
    It will be refactored later. The idea is to have something working
    quickly.
    """
    docFactory = loaders.xmlstr("""
  <div id="resultsDiv" xmlns="http://www.w3.org/1999/xhtml" xmlns:nevow="http://nevow.com/ns/nevow/0.1" >
    <table class="results" nevow:render="sequence" nevow:data="results">
      <tr nevow:pattern="item" nevow:render="row">
        <td>
          <div class="resultItem">
            <table>
              <tr><td><div><nevow:attr name="class"><nevow:slot name="mime_type"/></nevow:attr></div></td>
                  <td>
                   <a class="distantDocTitle">
                    <nevow:attr name="href"><nevow:slot name="distanturl" /></nevow:attr>
                    <nevow:slot name="doctitle">DOC TITLE</nevow:slot>
                   </a>
                  </td>
              </tr>
            </table>
            <div class="resultDesc"><nevow:slot name="abstract" /></div>
            <span class="resultUrl">(<span nevow:render="peer" />) - <nevow:slot name="docurl" /> - <nevow:slot name="readable_size" /> - <nevow:slot name="publication_date" /></span>
          </div>
        </td>
      </tr>
    </table>
    <div class="prevnext"><a><nevow:attr name="href"
    nevow:render="prevset_url"/>Previous</a> - <a><nevow:attr
    name="href" nevow:render="nextset_url"/>Next</a></div>
    <nevow:invisble nevow:macro="footer" />
  </div>
    """)
    
    def __init__(self, results, provider, query, queryId):
        self.results = results
        self.peerLogin, self.peerHost, self.peerPort = provider
        self.query = query
        self.queryId = queryId

    def render_peer(self, context, data):
        return '%s (%s:%s)' % (self.peerLogin, self.peerHost, self.peerPort)

    def render_row(self, context, data):
        document = data
        ResultsPageMixIn.render_row(self, context, data)
        context.fillSlots('distanturl', '/distantfile?filepath=%s&docid=%s&host=%s&port=%s'\
                          % (document.url, document.document_id, self.peerHost, self.peerPort))
        return context.tag

    def render_nextset_url(self, context, data):
        # XXX find a better implementation later
        return 'search?words=%s&offset=%s&qid=%s' % ('+'.join(self.query.words),
                                                     self.query.offset + 15,
                                                     self.queryId)
    def render_prevset_url(self, context, data):
        offset = self.query.offset
        if offset:
            offset -= 15
        return 'search?words=%s&offset=%s&qid=%s' % ('+'.join(self.query.words),
                                                     offset,
                                                     self.queryId)


class ResultsPageFactory(athena.LivePageFactory):
    def getLivePage(self, context):
        livepageId = inevow.IRequest(context).getHeader('Livepage-Id')
        print "*** livepage id =", livepageId
        if livepageId is not None:
            return self.clients.get(livepageId)
        else:
            return None        

    def clientFactory(self, context, querier, p2pquerier):
        livepage = self.getLivePage(context)
        if livepage is None:
            return self._manufactureClient(context, querier, p2pquerier)
        else:
            return livepage
        
    def _manufactureClient(self, context, querier, p2pquerier):
        print "Building livepage !"
        cl = self._pageFactory(context, querier, p2pquerier)
        cl.factory = self
        return cl

FACTORY = ResultsPageFactory(ResultsPage)
