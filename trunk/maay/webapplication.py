#
#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify it
#     under the terms of the GNU General Public License as published by the
#     Free Software Foundation; either version 2 of the License, or (at your
#     option) any later version.
#     
#     This program is distributed in the hope that it will be useful, but
#     WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
#     Public License for more details.
#     
#     You should have received a copy of the GNU General Public License along
#     with this program; if not, write to the Free Software Foundation, Inc.,
#     59 Temple Place - Suite 330, Boston, MA 02111-1307 USA.
#     


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

from nevow import rend, tags, loaders, athena, inevow, url

from logilab.common.textutils import normalize_text
from logilab.common.compat import set

from maay import VERSION
from maay.querier import IQuerier, WEB_AVATARID
from maay.configuration import get_path_of, INDEXER_CONFIG, NODE_CONFIG
from maay.texttool import makeAbstract, WORDS_RGX, normalizeText, boldifyText
from maay.query import Query, parseWords
from maay.p2pquerier import P2pQuerier, P2pQuery
from maay.dbentity import ScoredDocument, Document
import maay.indexer as indexer
from maay.localinfo import NODE_LOGIN

def _is_valid_directory(directory):
    try:
        mode = os.stat(directory)[stat.ST_MODE]
        if not stat.S_ISDIR(mode):
            return False
    except:
        return False
    return True


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

    def render_custom_htmlheader(self, context):
        return ''

    def render_onload(self, context):
        return ''
    
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
        self.indexerConfig = INDEXER_CONFIG
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

    def updateStatus(self, message, private, public):
        self.callRemote('updateStatus', message, private, public)

    def countersUpdated(self, old, new, private, public):
        self.updateStatus(u'Indexation in progress - %s new documents / %s total' %
                          (new, old + new), private, public)

    def indexationCompleted(self, old, new, private, public):
        self.updateStatus(u'Indexation finished - %s new documents / %s total'
            % (new, old + new), private, public)

    def updatePrivateDocumentCount(self, count):
        self.callRemote('updatePrivateDocumentCount', count)

    def updatePublicDocumentCount(self, count):
        self.callRemote('updatePublicDocumentCount', count)

    def render_privateDocumentCount(self, context, data):
        querier = IQuerier(context)
        return querier.getDocumentCount()[Document.PRIVATE_STATE]

    def render_publicDocumentCount(self, context, data):
        querier = IQuerier(context)
        return querier.getDocumentCount()[Document.PUBLISHED_STATE]

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
        self.privateDocuments = 0
        self.publicDocuments = 0
    
    def newDocumentIndexed(self, filename, state):
        self.indexedDocuments += 1
        if state == Document.PRIVATE_STATE:
            self.privateDocuments += 1
        elif state == Document.PUBLISHED_STATE:
            self.publicDocuments += 1
        # refresh pages for each group of 10 indexed files
        if (self.indexedDocuments % 10) == 0:
            for webpage in self.clients.itervalues():
                webpage.countersUpdated(self.untouchedDocuments,
                                        self.indexedDocuments,
                                        self.privateDocuments,
                                        self.publicDocuments)
                # webpage.updatePrivateDocumentCount(self.privateDocuments)
                # webpage.updatePublicDocumentCount(self.publicDocuments)
        
    def documentUntouched(self, filename, state):
        self.untouchedDocuments += 1
        if state == Document.PRIVATE_STATE:
            self.privateDocuments += 1
        elif state == Document.PUBLISHED_STATE:
            self.publicDocuments += 1
        if (self.untouchedDocuments % 10) == 0:
            for webpage in self.clients.itervalues():
                webpage.countersUpdated(self.untouchedDocuments,
                                        self.indexedDocuments,
                                        self.privateDocuments,
                                        self.publicDocuments)
    
    def indexationCompleted(self):
        for webpage in self.clients.itervalues():
            webpage.indexationCompleted(self.untouchedDocuments,
                                        self.indexedDocuments,
                                        self.privateDocuments,
                                        self.publicDocuments)
            # webpage.updatePrivateDocumentCount(self.privateDocuments)
            # webpage.updatePublicDocumentCount(self.publicDocuments)
        # reset counters after indexation is finished
        self.untouchedDocuments = 0
        self.indexedDocuments = 0
        self.privateDocuments = 0
        self.publicDocuments = 0
    
class SearchForm(MaayPage):
    """default search form"""
    bodyFactory = loaders.xmlfile(get_path_of('searchform.html'))
    addSlash = True
    child_versionjs = static.File(get_path_of('version.js'))
    
    def __init__(self, maayId, querier, p2pquerier=None):
        MaayPage.__init__(self, maayId)
        self.querier = querier
        self.p2pquerier = p2pquerier
        self.download_dir = INDEXER_CONFIG.download_dir
        # We really want that information to be accessible trhough any client
        setattr(self, 'child_localversion.js', 'current_version = "%s";' % VERSION)

    def render_custom_htmlheader(self, context):
        return [
            tags.script(type='text/javascript', src='http://maay.netofpeers.net/version.js'),
            tags.script(type='text/javascript', src=url.here.child('localversion.js')),
            tags.script(type='text/javascript', src=url.here.child('versionjs')),
            ]

    def render_onload(self, context):
        return 'checkNewRelease();'

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

    def child_peers(self, context):
        return PeersList(self.maayId, self.querier)

    def child_indexation(self, context, _factory=IndexationPageFactory(IndexationPage)):
        alertMsg = ""
        context.remember(self.querier, IQuerier)
        INDEXER_CONFIG.load_from_files()
        # TODO: check if the added folders are valid
        # Actions (add/remove) on private folders
        addPrivateFolder = context.arg('addPrivateFolder', 0)
        if addPrivateFolder:
            if _is_valid_directory(addPrivateFolder):
                INDEXER_CONFIG.private_dir.append(addPrivateFolder)
                INDEXER_CONFIG.save()
            else:
                alertMsg = "\\'%s\\' is not a valid folder" % addPrivateFolder
 
        removePrivateFolder = context.arg('removePrivateFolder', 0)
        if removePrivateFolder:
            try:
                INDEXER_CONFIG.private_dir.remove(removePrivateFolder)
                INDEXER_CONFIG.save()
            except ValueError:
                print "Folder '%s' not in the private directory list"

        # Actions (add/remove) on public folders
        addPublicFolder = context.arg('addPublicFolder', 0)
        if addPublicFolder:
            if _is_valid_directory(addPublicFolder):
                INDEXER_CONFIG.public_dir.append(addPublicFolder)
                INDEXER_CONFIG.save()
            else:
                alertMsg = "\\'%s\\' is not a valid folder" % addPublicFolder
 
        removePublicFolder = context.arg('removePublicFolder', 0)
        if removePublicFolder:
            try:
                INDEXER_CONFIG.public_dir.remove(removePublicFolder)
                INDEXER_CONFIG.save()
            except ValueError:
                print "Folder '%s' not in the private directory list"

        # Actions (add/remove) on skipped folders
        addSkippedFolder = context.arg('addSkippedFolder', 0)
        if addSkippedFolder:
            if _is_valid_directory(addSkippedFolder):
                INDEXER_CONFIG.skip_dir.append(addSkippedFolder)
                INDEXER_CONFIG.save()
            else:
                alertMsg = "\\'%s\\' is not a valid folder" % addSkippedFolder
 
        removeSkippedFolder = context.arg('removeSkippedFolder', 0)
        if removeSkippedFolder:
            try:
                INDEXER_CONFIG.skip_dir.remove(removeSkippedFolder)
                INDEXER_CONFIG.save()
            except ValueError:
                print "Folder '%s' not in the private directory list"

        start = int(context.arg('start', 0))
        indexationPage = _factory.clientFactory(context)

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
                nodeConfig = INodeConfiguration(context)
                indexer.start_as_thread(nodeConfig, _factory)
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
        words, _ = parseWords(context.arg('words'))
        docurl = self.querier.notifyDownload(docid, words)
        if docurl:
            if osp.isfile(docurl):
                return static.File(docurl)
            else:
                #TODO: automatically reindex
                return Maay404("File %s does not exist any more. Please re-index." %
                               docurl)
        else:
            return Maay404()

    def child_distantfile(self, context):
        """download distant file and put it in a public indexable directory"""
        host = context.arg('host')
        port = context.arg('port')
        qid = context.arg('qid')
        words = context.arg('words').split()
        filename = context.arg('filename')
        docid = context.arg('docid')
        if not host or not port or not docid:
            return Maay404()
        nodeConfig = INodeConfiguration(context)
        proxy = Proxy(str('http://%s:%s' % (host, port)))
        print "[webapp] trying to donwload %r from %s:%s" % (filename, host, port)
        d = proxy.callRemote('downloadFile', docid, words)
        d.addCallback(self.gotDataBack, nodeConfig, filename, words)
        d.addErrback(self.tryOtherProviders, nodeConfig, filename, words, host,
                     port, docid, qid)
        return d

    def gotDataBack(self, rpcFriendlyData, nodeConfig, filename, words):
        if rpcFriendlyData:
            fileData = rpcFriendlyData.data
        else:
            # this will trigger the errback in child_distantfile
            raise Exception("File cannot be downloaded from this host")
        print " ... downloaded !"
        filepath = osp.join(self.download_dir, filename)
        f = file(filepath,'wb')
        f.write(fileData)
        f.close()
        return DistantFilePage(nodeConfig, filepath, words)

    def onDownloadFileError(self, error, filename):
        msg = "Error while downloading file: %s" % (filename,)
        return Maay404(msg)

    def tryOtherProviders(self, error, nodeConfig, filename, words, host, port, docId, qid):
        """starts to explore the list of other providers"""
        providers = self.querier.getProvidersFor(docId, qid)
        self.providerSet = set(providers)
        self.providerSet.remove((host, int(port)))
        return self.retryWithOtherProvider('...', nodeConfig, words, docId, filename)
    
    def retryWithOtherProvider(self, error, nodeConfig, words, docId, filename):
        if self.providerSet:
            nextHost, nextPort = self.providerSet.pop()
            print "[webapp] trying to donwload %r from %s:%s" % (filename, nextHost, nextPort)
            proxy = Proxy(str('http://%s:%s' % (nextHost, nextPort)))
            d = proxy.callRemote('downloadFile', docId, words)
            d.addCallback(self.gotDataBack, nodeConfig, filename, words)
            d.addErrback(self.retryWithOtherProvider, nodeConfig, words, docId, filename)
            return d
        else:
            return self.onDownloadFileError('no provider available', filename)


class DistantFilePage(static.File):
    def __init__(self, nodeConfig, filepath, words):
        static.File.__init__(self, filepath)
        self.filepath = filepath
        docId = indexer.indexJustOneFile(nodeConfig, self.filepath, words)

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
        localCount, distantCount = self.querier.countResults(self.qid)
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
        localCount, _ = self.querier.countResults(self.qid)
        return localCount

    def render_distantcount(self, context, data):
        _, distantCount = self.querier.countResults(self.qid)
        return distantCount

    def render_totalcount(self, context, data):
        localCount, distantCount = self.querier.countResults(self.qid)
        return localCount + distantCount

    def render_searchfield(self, context, data):
        context.fillSlots('words', self.query.joinwords(' ')) #WORDS
        return context.tag

    def render_next(self, context, data):
        """computes 'Next' link"""
        localCount, distantCount = self.querier.countResults(self.qid)
        if self.onlyDistant:
            resultsCount = distantCount
        elif self.onlyLocal:
            resultsCount = localCount
        else:
            resultsCount = localCount + distantCount
        offset = self.query.offset
        if (offset + 15) < resultsCount:
            return tags.xml('<a href="javascript: browseResults(%s);">Next</a>' % (offset + 15))
        return tags.xml('<span class="selectedCriterium">Next</span>')
        
    
    def render_previous(self, context, data):
        """computes 'Previous' link"""
        if self.query.offset <= 0:
            return tags.xml('<span class="selectedCriterium">Previous</span>')
        offset = self.query.offset - 15
        return tags.xml('<a href="javascript: browseResults(%s);">Previous</a>' % (offset))
    
    def render_peer(self, context, data):
        """:type data: Result"""
        if data.port == 0:
            return ''
        return '%s (%s) - ' % (data.login, data.host)

    def render_relevanceDiv(self, context, data):
        if self.query.order == 'relevance':
            return tags.xml('<span class="selectedCriterium">'
                            'relevance</span>')
        else:
            return tags.xml("""<span class="unselectedCriterium"><a href="javascript: sortBy('relevance');">"""
                            'relevance</a></span>')

    def render_popularityDiv(self, context, data):
        if self.query.order == 'popularity':
            return tags.xml('<span class="selectedCriterium">'
                            'popularity</span>')
        else:
            return tags.xml("""<span class="unselectedCriterium"><a href="javascript: sortBy('popularity');">"""
                            'popularity</a></span>')

    def render_publicationDiv(self, context, data):
        if self.query.order == 'publication_time':
            return tags.xml('<span class="selectedCriterium">'
                            'publication time</span>')
        else:
            return tags.xml("""<span class="unselectedCriterium"><a href="javascript: sortBy('publication_time');">"""
                            'publication time</a></span>')

    def render_localResultsDiv(self, context, data):
        if self.onlyLocal:
            return tags.xml('<span class="selectedLocalResults">local results</span>')
        else:
            return tags.xml('<span class="localPublicResults">'
                            '<a href="javascript: onlyLocalResults();">local results</a></span>')

    def render_distantResultsDiv(self, context, data):
        if self.onlyDistant:
            return tags.xml('<span class="selectedDistantResults">distant results</span>')
        else:
            return tags.xml('<span class="distantResults">'
                            '<a href="javascript: onlyDistantResults();">distant results</a></span>')

    def render_allResultsDiv(self, context, data):
        if not (self.onlyLocal or self.onlyDistant):
            return tags.xml('<span class="selectedAllResults">all results</span>')
        else:
            return tags.xml('<span class="allResults">'
                            '<a href="javascript: allResults();">all results</a></span>')
           


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
            context.fillSlots('resultClass', "localPublicResults")
            context.fillSlots('providersCount', '')
        else:
            baseurl = '/distantfile?docid=%s' % (document.document_id,)
            context.fillSlots('resultClass', "distantResults")
            baseurl += '&host=%s' % (document.host,)
            baseurl += '&port=%s' % (document.port,)
            context.fillSlots('providersCount', 'Provided by %s node(s)' %
                              (len(self.querier.getProvidersFor(document.document_id,
                                                                self.qid))))
        baseurl += '&filename=%s' % osp.basename(document.url)
        baseurl += '&words=%s' % '+'.join(self.query.words)
        baseurl += '&qid=%s' % (self.qid,)
        context.fillSlots('url', baseurl)
        context.fillSlots('relevance', document.relevance)
        context.fillSlots('popularity', document.popularity)
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
            self.qid = p2pQuery.qid
            self.p2pQuery = p2pQuery
            # purge old results
            self.querier.purgeOldResults()
            provider = (NODE_LOGIN, NODE_CONFIG.get_node_id(), 'localhost', 0)
            self.querier.pushDocuments(self.qid, results, provider)
            self.results = self.querier.getQueryResults(self.query)
            
    # XXX (refactoring): provide a common base class for LivePages
    # Maay / py2exe / win32 related trick : we provide our own javascript
    # files, so we need to override the default LivePage mechanism
    # to find them
    def childFactory(self, ctx, name):
        if name in self._javascript:
            return static.File(get_path_of(self._javascript[name]))
        
    def onNewResults(self, provider, results):
        results = [ScoredDocument(**params) for params in results]
        self.querier.pushDocuments(self.qid, results, provider)
        results = self.querier.getQueryResults(self.query,
                                               onlyLocal=self.onlyLocal,
                                               onlyDistant=self.onlyDistant)
        page = PleaseCloseYourEyes(results, self.querier, self.query, self.qid,
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
        results = self.querier.getQueryResults(self.query,
                                               onlyLocal=self.onlyLocal,
                                               onlyDistant=self.onlyDistant)
        page = PleaseCloseYourEyes(results, self.querier, self.query, self.qid,
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
    
    def remote_sortBy(self, context, sortCriteria):
        self.query.order = sortCriteria
        # reset counter to 0
        return self.remote_browseResults(context, 0)

    
class PleaseCloseYourEyes(rend.Page, ResultsPageMixIn):
    """This resource and the way it is called is kind of ugly.
    It will be refactored later. The idea is to have something working
    quickly.
    """
    docFactory = loaders.xmlfile(get_path_of('livefragment.html'))
    
    def __init__(self, results, querier, query, qid,
                 onlyLocal=False, onlyDistant=False):
        self.results = results
        self.querier = querier
        self.query = query
        self.qid = qid
        self.onlyLocal = onlyLocal
        self.onlyDistant = onlyDistant


class ResultsPageFactory(athena.LivePageFactory):
    def getLivePage(self, context):
        livepageId = inevow.IRequest(context).getHeader('Livepage-Id')
        #print "*** livepage id =", livepageId
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
