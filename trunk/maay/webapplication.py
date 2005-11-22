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


"""maay local web UI script"""

__revision__ = '$Id$'

from datetime import datetime
from itertools import cycle
from tempfile import mkdtemp
import os, os.path as osp
import stat

from zope.interface import Interface, implements
from twisted.web import static
from twisted.web.xmlrpc import Proxy
from twisted.internet import reactor
from twisted.python import log

from nevow import rend, tags, loaders, athena, inevow

from logilab.common.textutils import normalize_text
from logilab.common.compat import set

from maay.querier import WEB_AVATARID
from maay.configuration import get_path_of
from maay.texttool import makeAbstract, WORDS_RGX, normalizeText, boldifyText
from maay.query import Query
from maay.p2pquerier import P2pQuerier, P2pQuery
from maay.dbentity import Document
from maay import indexer 


class INodeConfiguration(Interface):
    """provide an interface in order to be able to remember webappconfig"""


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

class Maay404(MaayPage, rend.FourOhFour):
    """Maay specific resource for 404 errors"""
    # loader = loaders.xmlfile(get_path_of('notfound.html'))
    bodyFactory = loaders.xmlfile(get_path_of('notfound.html'))
    
    def __init__(self, msg="Sorry, I could not find the requested resource."):
        MaayPage.__init__(self)
        self.msg = msg

    def render_errormsg(self, context, data):
        return self.msg
    
    def renderHTTP_notFound(self, context):
        """Render a not found message to the given request.
        """
        # XXX little trick (extends MaayPage, etc.)
        return self.renderString(context)
        # return self.loader.load(context)[0]

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


class IndexationPage(athena.LivePage):
    docFactory = loaders.xmlfile(get_path_of('indexationpage.html'))

    def __init__(self):
        athena.LivePage.__init__(self)
        self.indexerConfig = indexer.indexerConfig
        self.msg = 'not running'

    def macro_footer(self, context):
        return loaders.xmlfile(get_path_of('footer.html'))

    def remote_live(self, context):
        """let's start !"""
        return 0

    # XXX (refactoring): provide a common base class for LivePages
    # Maay / py2exe / win32 related trick : we provide our own javascript
    # files, so we need to override the default LivePage mechanism
    # to find them
    def childFactory(self, ctx, name):
        if name in self._javascript:
            return static.File(get_path_of(self._javascript[name]))

    def updateStatus(self, message):
        self.callRemote('updateStatus', message)

    def countersUpdated(self, old, new):
        self.updateStatus(u'Indexation in progress - %s new documents / %s total' %
                          (new, old + new))

    def indexationCompleted(self):
        self.updateStatus(u'Indexation finished - %s new documents / %s total'
            % (IndexationPage.indexedDocuments, IndexationPage.indexedDocuments + IndexationPage.untouchedDocuments))

    def render_message(self, context, data):
        return self.msg

    def render_alert(self, context, data):
        context.fillSlots("message", self.alertmessage)
        return context.tag

    def data_privatefolders(self, context, data):
        if not self.indexerConfig.private_dir:
            return ["No private folder."]
        return self.indexerConfig.private_dir

    def data_publicfolders(self, context, data):
        if not self.indexerConfig.public_dir:
            return ["No public folder."]
        return self.indexerConfig.public_dir

    def data_skippedfolders(self, context, data):
        if not self.indexerConfig.skip_dir:
            return ["No skipped folders."]
        return self.indexerConfig.skip_dir

    def render_directory(self, context, name):
        print "directory = %s" % name
        context.fillSlots("name", name)
        return context.tag

class IndexationPageFactory(athena.LivePageFactory):
    implements(indexer.IIndexerObserver)

    def __init__(self, pageFactory):
        athena.LivePageFactory.__init__(self, pageFactory)
        self.untouchedDocuments = 0
        self.indexedDocuments = 0

    def newDocumentIndexed(self, filename):
        self.indexedDocuments += 1
        # refresh pages for each group of 10 indexed files
        if (self.indexedDocuments % 10) == 0:
            for webpage in self.clients.itervalues():
                webpage.countersUpdated(self.untouchedDocuments,
                                        self.indexedDocuments)
        
    def documentUntouched(self, filename):
        self.untouchedDocuments += 1
        if (self.untouchedDocuments % 10) == 0:
            for webpage in self.clients.itervalues():
                webpage.countersUpdated(self.untouchedDocuments,
                                        self.indexedDocuments)
    
    def indexationCompleted(self):
        for webpage in self.clients.itervalues():
            webpage.indexationCompleted()
        # reset counters after indexation is finished
        self.untouchedDocuments = 0
        self.indexedDocuments = 0
    

class SearchForm(MaayPage):
    """default search form"""
    bodyFactory = loaders.xmlfile(get_path_of('searchform.html'))
    addSlash = True

    def __init__(self, maayId, querier, p2pquerier=None):
        MaayPage.__init__(self, maayId)
        self.querier = querier
        self.p2pquerier = p2pquerier
        self.download_dir = indexer.indexerConfig.download_dir

    # TODO: since getDocumentCount might be quite costly to compute for the
    # DBMS, cache the value and update it every 10 mn
    def render_shortstat(self, context, data):
        docCounts = self.querier.getDocumentCount()
        context.fillSlots('localDocumentCount', docCounts[Document.PRIVATE_STATE] + docCounts[Document.PUBLISHED_STATE]) 
        context.fillSlots('publicDocumentCount', docCounts[Document.PUBLISHED_STATE]) 
        return context.tag
        
    def logout(self):
        print "Bye %s !" % (self.maayId,)
        # XXX: logout message should be forwarded to presence server
        return None

    # FIXME: maybe not a good place to define this function ?
    def __is_valid_directory(self, directory):
        try:
            mode = os.stat(directory)[stat.ST_MODE]
            if not stat.S_ISDIR(mode):
                return False
        except:
            return False
        return True

    def child_indexation(self, context, _factory=IndexationPageFactory(IndexationPage)):
        alertMsg = ""
        # TODO: check if the added folders are valid

        # Actions (add/remove) on private folders

        addPrivateFolder = context.arg('addPrivateFolder', 0)
        if addPrivateFolder:
            if self.__is_valid_directory(addPrivateFolder):
                indexer.indexerConfig.private_dir.append(addPrivateFolder)
                indexer.indexerConfig.save()
            else:
                alertMsg = "\\'%s\\' is not a valid folder" % addPrivateFolder
 
        removePrivateFolder = context.arg('removePrivateFolder', 0)
        if removePrivateFolder:
            try:
                indexer.indexerConfig.private_dir.remove(removePrivateFolder)
                indexer.indexerConfig.save()
            except ValueError:
                print "Folder '%s' not in the private directory list"

        # Actions (add/remove) on public folders
        addPublicFolder = context.arg('addPublicFolder', 0)
        if addPublicFolder:
            if self.__is_valid_directory(addPublicFolder):
                indexer.indexerConfig.public_dir.append(addPublicFolder)
                indexer.indexerConfig.save()
            else:
                alertMsg = "\\'%s\\' is not a valid folder" % addPublicFolder
 
        removePublicFolder = context.arg('removePublicFolder', 0)
        if removePublicFolder:
            try:
                indexer.indexerConfig.public_dir.remove(removePublicFolder)
                indexer.indexerConfig.save()
            except ValueError:
                print "Folder '%s' not in the private directory list"

        # Actions (add/remove) on skipped folders
        addSkippedFolder = context.arg('addSkippedFolder', 0)
        if addSkippedFolder:
            if self.__is_valid_directory(addSkippedFolder):
                indexer.indexerConfig.skip_dir.append(addSkippedFolder)
                indexer.indexerConfig.save()
            else:
                alertMsg = "\\'%s\\' is not a valid folder" % addSkippedFolder
 
        removeSkippedFolder = context.arg('removeSkippedFolder', 0)
        if removeSkippedFolder:
            try:
                indexer.indexerConfig.skip_dir.remove(removeSkippedFolder)
                indexer.indexerConfig.save()
            except ValueError:
                print "Folder '%s' not in the private directory list"

        start = int(context.arg('start', 0))
        indexationPage = _factory.clientFactory(context)

        # FIXME: porky way to pass the querier ref to the indexationPage
        IndexationPage.querier = self.querier
        indexationPage.updateDocumentStats()
        
	if start == 0:
            if indexer.is_running():
                msg = "Indexer running"
            else:
                msg = "Indexer not running"
        else:
            if indexer.is_running():    
                msg = "Indexer already running"
            else:
                msg = "Indexer started"
                indexer.start_as_thread(_factory)
        indexationPage.msg = msg
        indexationPage.alertmessage = alertMsg
        return indexationPage

    def child_search(self, context):
        return FACTORY.clientFactory(context, self.querier, self.p2pquerier)
    
    # XXX make sure that the requested document is really in the database
    # XXX don't forget to update the download statistics of the document
    def child_download(self, context):
        """download *local* file"""
        docid = context.arg('docid')
        query = Query.fromRawQuery(unicode(context.arg('words'), 'utf-8'))
        docurl = self.querier.notifyDownload(docid, query.words)
        if docurl:
            if osp.isfile(docurl):
                return static.File(docurl)
            else:
                return Maay404("File %s does not exist any more. Please re-index." %
                               docurl)
        else:
            return Maay404()

    def child_distantfile(self, context):
        """download distant file and put it in a public indexable directory"""
        host = context.arg('host')
        port = context.arg('port')
        queryId = context.arg('qid')
        words = context.arg('words').split()
        filename = context.arg('filename')
        docid = context.arg('docid')
        if not host or not port or not docid:
            return Maay404()
        self.proivderSet = set()
        proxy = Proxy('http://%s:%s' % (host, port))
        d = proxy.callRemote('downloadFile', docid, words)
        d.addCallback(self.gotDataBack, filename)
        d.addErrback(self.tryOtherProviders, filename, words, host,
                     port, docid, queryId)
        return d

    def gotDataBack(self, rpcFriendlyData, filename):
        fileData = rpcFriendlyData.data
        print " ... downloaded !"
        filepath = osp.join(self.download_dir, filename)
        f=file(filepath,'wb')
        f.write(fileData)
        f.close()
        return DistantFilePage(filepath)

    def onDownloadFileError(self, error, filename):
        msg = "Error while downloading file: %s" % (filename,)
        return Maay404(msg)

    def tryOtherProviders(self, error, filename, words, host, port, docId, queryId):
        """starts to explore the list of other providers"""
        providers = self.querier.getProvidersFor(docId, queryId)
        self.providerSet.remove((host, port))
        return self.retryWithOtherProvider(words, docId, filename)
    
    def retryWithOtherProvider(self, words, docId, filename):
        if self.providerSet:
            nextHost, nextPort = self.providerSet.pop()
            proxy = Proxy('http://%s:%s' % (nextHost, nextPort))
            d = proxy.callRemote('downloadFile', docId, words)
            d.addCallback(self.gotDataBack, filename)
            d.addErrback(self.retryWithOtherProvider, words, docId, filename)
            return d
        else:
            return self.onDownloadFileError('no provider available', filename)
    
    
class DistantFilePage(static.File):
    def __init__(self, filepath):
        static.File.__init__(self, filepath)
        self.filepath = filepath
        indexer.indexJustOneFile(self.filepath)

class ResultsPageMixIn:

    def data_results(self, context, data):
        return self.results
    
    def macro_footer(self, context):
        return loaders.xmlfile(get_path_of('footer.html'))

    def macro_prevnext(self, context):
        return loaders.xmlfile(get_path_of('prevnext.html'))

    def macro_resultset(self, context):
        return loaders.xmlfile(get_path_of('livefragment.html'))
    
    def render_title(self, context, data):
        localCount, distantCount = self.querier.countResults(self.queryId)
        if self.onlyDistant:
            resultsCount = distantCount
        elif self.onlyLocal:
            resultsCount = localCount
        else:
            resultsCount = localCount + distantCount
        offset = self.query.offset
        context.fillSlots('words', self.query.joinwords(' ')) #WORDS
        context.fillSlots('start_result', min(resultsCount, offset + 1))
        context.fillSlots('end_result', min(resultsCount, offset+15))
        context.fillSlots('count', resultsCount)
        return context.tag

    def render_localcount(self, context, data):
        localCount, _ = self.querier.countResults(self.queryId)
        return localCount

    def render_distantcount(self, context, data):
        _, distantCount = self.querier.countResults(self.queryId)
        return distantCount

    def render_totalcount(self, context, data):
        localCount, distantCount = self.querier.countResults(self.queryId)
        return localCount + distantCount

    def render_searchfield(self, context, data):
        context.fillSlots('words', self.query.joinwords(' ')) #WORDS
        return context.tag

    def render_next(self, context, data):
        """computes 'Next' link"""
        localCount, distantCount = self.querier.countResults(self.queryId)
        if self.onlyDistant:
            resultsCount = distantCount
        elif self.onlyLocal:
            resultsCount = localCount
        else:
            resultsCount = localCount + distantCount
        offset = self.query.offset
        if (offset + 15) < resultsCount:
            return tags.xml('<a href="javascript: browseResults(%s);">Next</a>' % (offset + 15))
        return ''
        
    
    def render_previous(self, context, data):
        """computes 'Previous' link"""
        if self.query.offset <= 0:
            return ''
        offset = self.query.offset - 15
        return tags.xml('<a href="javascript: browseResults(%s);">Previous</a>' % (offset))
    
    def render_peer(self, context, data):
        """:type data: Result"""
        if data.login is None:
            return ''
        return '%s (%s) - ' % (data.login, data.host)
    
    def render_row(self, context, data):
        document = data
        words = self.query.words #WORDS (was .split())
        context.fillSlots('mime_type', document.mime_type.replace('/', '_'))
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
        context.fillSlots('docurl', tags.xml(boldifyText(document.url, words)))
        context.fillSlots('words', self.query.joinwords(' ')) #WORDS
        context.fillSlots('readable_size', document.readable_size())
        date = datetime.fromtimestamp(document.publication_time)
        context.fillSlots('publication_date', date.strftime('%d %b %Y'))
        if document.host == 'localhost':
            baseurl = '/download?docid=%s' % (document.document_id,)
            # TODO: make a difference between private and public results
            context.fillSlots('resultClass', "localPublicResult")
        else:
            baseurl = '/distantfile?docid=%s' % (document.document_id,)
            context.fillSlots('resultClass', "distantResult")
            baseurl += '&host=%s' % (document.host,)
            baseurl += '&port=%s' % (document.port,)
        baseurl += '&filename=%s' % osp.basename(document.url)
        baseurl += '&words=%s' % '+'.join(self.query.words)
        baseurl += '&qid=%s' % (self.queryId,)
        context.fillSlots('url', baseurl)
        return context.tag
    

class ResultsPage(athena.LivePage, ResultsPageMixIn):
    """default results page"""
    child_maaycss = static.File(get_path_of('maay.css'))
    child_images = static.File(get_path_of('images/'))
    docFactory = loaders.xmlfile(get_path_of('liveresults.html'))
    addSlash = False

    def __init__(self, context, querier, p2pquerier):
        athena.LivePage.__init__(self)
        # NOTE: At the time this comment is written, athena/LivePages are handled
        #       differently in nevow SVN. It's now possible to insantiate directly
        #       LivePage instances (which is great !), so we'll have to change
        #       the implementation for next nevow release.
        self.querier = querier
        self.p2pquerier = p2pquerier
        self.query = Query.fromContext(context)
        self.offset = self.query.offset
        self.onlyLocal = False
        self.onlyDistant = False
        # push local results once for all
        if len(inevow.IRemainingSegments(context)) < 2:
            # only store abstracts in the results table
            results = []
            for localDoc in querier.findDocuments(self.query):
                localDoc.text = makeAbstract(localDoc.text, self.query.words)
                results.append(localDoc)
            webappConfig = INodeConfiguration(context)
            p2pQuery = P2pQuery(sender=webappConfig.get_node_id(),
                                query=self.query)
            self.queryId = p2pQuery.qid
            self.p2pQuery = p2pQuery
            # purge old results
            self.querier.purgeOldResults()
            self.querier.pushDocuments(self.queryId, results, provider=None)
            self.results = self.querier.getQueryResults(self.queryId, offset=0)
            
    # XXX (refactoring): provide a common base class for LivePages
    # Maay / py2exe / win32 related trick : we provide our own javascript
    # files, so we need to override the default LivePage mechanism
    # to find them
    def childFactory(self, ctx, name):
        if name in self._javascript:
            return static.File(get_path_of(self._javascript[name]))
        
    def onNewResults(self, provider, results):
        results = [Document(**params) for params in results]
        self.querier.pushDocuments(self.queryId, results, provider)
        results = self.querier.getQueryResults(self.queryId, offset=self.query.offset,
                                               onlyLocal=self.onlyLocal,
                                               onlyDistant=self.onlyDistant)
        page = PleaseCloseYourEyes(results, self.querier, self.query, self.queryId,
                                   self.onlyLocal, self.onlyDistant).renderSynchronously()
        page = unicode(page, 'utf-8')
        self.callRemote('updateResults', page)

    def remote_connect(self, context):
        """just here to start the connection between client and server (Ajax)"""
        #TODO: very soon, the line below will also be the p2pquerier's job
        self.query.offset = 0
        self.p2pquerier.sendQuery(self.p2pQuery)
        self.p2pquerier.addAnswerCallback(self.p2pQuery.qid, self.onNewResults)
        # self.querier.pushDocuments(self.queryId, self.results, provider=None)
        return u''
    
    def remote_browseResults(self, context, offset):
        self.query.offset = offset
        results = self.querier.getQueryResults(self.queryId, offset=offset,
                                               onlyLocal=self.onlyLocal,
                                               onlyDistant=self.onlyDistant)
        page = PleaseCloseYourEyes(results, self.querier, self.query, self.queryId,
                                   self.onlyLocal, self.onlyDistant).renderSynchronously()
        page = unicode(page, 'utf-8')
        return page

    def remote_setLocalFlag(self, context, flag):
        self.onlyLocal = flag
        self.onlyDistant = False
        self.query.offset = 0
        return self.remote_browseResults(context, self.query.offset)

    def remote_setDistantFlag(self, context, flag):
        self.onlyDistant = flag
        self.onlyLocal = False
        self.query.offset = 0
        return self.remote_browseResults(context, self.query.offset)

    def remote_unsetFlags(self, context):
        self.onlyDistant = False
        self.onlyLocal = False
        self.query.offset = 0
        return self.remote_browseResults(context, self.query.offset)
    

class PleaseCloseYourEyes(rend.Page, ResultsPageMixIn):
    """This resource and the way it is called is kind of ugly.
    It will be refactored later. The idea is to have something working
    quickly.
    """
    docFactory = loaders.xmlfile(get_path_of('livefragment.html'))
    
    def __init__(self, results, querier, query, queryId,
                 onlyLocal=False, onlyDistant=False):
        self.results = results
        self.querier = querier
        self.query = query
        self.queryId = queryId
        self.onlyLocal = onlyLocal
        self.onlyDistant = onlyDistant


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
