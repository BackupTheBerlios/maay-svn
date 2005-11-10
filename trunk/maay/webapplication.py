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

from zope.interface import Interface
from twisted.web import static
from nevow import rend, tags, loaders

from logilab.common.textutils import normalize_text

from maay.querier import WEB_AVATARID
from maay.configuration import get_path_of
from maay.texttool import makeAbstract, WORDS_RGX, normalizeText, boldifyText
from maay.query import Query
from maay.p2pquerier import P2pQuerier, P2pQuery
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

    def _askForPeerResults(self, query, context):
        """Launches a P2P cascade of queries
           The result of this shall be used ~ 5 and 15 secs. later
           by the ResultPage
        """
        if not self.p2pquerier:
            print "BUG ? We don't have a P2pQuerier"
            return
        webappConfig = INodeConfiguration(context)
        theDistributedQuery = P2pQuery(webappConfig.get_node_id(),
                                       webappConfig.rpcserver_port,
                                       query)
        
        self.p2pquerier.sendQuery(theDistributedQuery)
        self.oldContext = context


    def child_search(self, context):
        # query = unicode(context.arg('words'))        
        offset = int(context.arg('offset', 0))
        words = context.arg('words')
        if not words:
            query = Query.fromRawQuery('')
            return FACTORY.getLivePage(context)
        rawQuery = unicode(context.arg('words'), 'utf-8')
        query = Query.fromRawQuery(rawQuery, offset)
        localResults = self.querier.findDocuments(query)
        # self._askForPeerResults(query, context)
        resultsPage = FACTORY.clientFactory(context, self.maayId, localResults, query, offset)
        #######################
        webappConfig = INodeConfiguration(context)
        p2pQuery = P2pQuery(webappConfig.get_node_id(),
                            webappConfig.rpcserver_port,
                            query)
        self.p2pquerier.sendQuery(p2pQuery)
        #######################

        self.p2pquerier.addAnswerCallback(p2pQuery.qid, resultsPage.onNewResults)
        return resultsPage
    
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


class IndexationPage(MaayPage):
    # just for the demo. Should be moved to a adminpanel interface later.
    """index page"""
    bodyFactory = loaders.xmlfile(get_path_of('indexationpage.html'))
    addSlash = False
    
    def __init__(self, msg = "No message"):
        MaayPage.__init__(self)
        self.__msg = msg

    def render_message(self, context, data):
        context.fillSlots('msg', self.__msg)
        return context.tag


from nevow import athena, inevow
from twisted.python import log

class ResultsPage(athena.LivePage):
    """default results page"""
    child_maaycss = static.File(get_path_of('maay.css'))
    child_images = static.File(get_path_of('images/'))
    docFactory = loaders.xmlfile(get_path_of('liveresults.html'))
    addSlash = False

    instances = []
    
    def __init__(self, maayId, results, query, offset):
        athena.LivePage.__init__(self)
        self.maayId = maayId
        self.results = results
        self.offset = offset
        self.query = query.words # unicode(query)

    def data_results(self, context, data):
        return self.results
    
    def render_title(self, context, data):
        context.fillSlots('words', self.query)
        context.fillSlots('start_result', min(len(self.results), self.offset + 1))
        context.fillSlots('end_result', self.offset + len(self.results))
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
        words = self.query.split()
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
        context.fillSlots('words', self.query)
        context.fillSlots('readable_size', document.readable_size())
        date = datetime.fromtimestamp(document.publication_time)
        context.fillSlots('publication_date', date.strftime('%d %b %Y'))
        return context.tag

    def onNewResults(self, results):
        # r = mergeResults(self.results, results)
        # source = htmlize(r)
        print "++++++++++++++++++ Got new resulsts", results
        self.callRemote('updateResults', u'<div>%r</div>' % results)

    def remote_foo(self, context):
        print "************************************************** le client m'appelle !!"
        return 0


class ResultsPageFactory(athena.LivePageFactory):
    def getLivePage(self, context):
        livepageId = inevow.IRequest(context).getHeader('Livepage-Id')
        print "*** livepage id =", livepageId
        if livepageId is not None:
            return self.clients.get(livepageId)
        else:
            return None        

    def clientFactory(self, context, maayId, results, query, offset):
        livepage = self.getLivePage(context)
        if livepage is None:
            return self._manufactureClient(maayId, results, query, offset)
        else:
            return livepage
        
    def _manufactureClient(self, maayId, results, query, offset):
        print "Building livepage !"
        cl = self._pageFactory(maayId, results, query, offset)
        cl.factory = self
        return cl

FACTORY = ResultsPageFactory(ResultsPage)
