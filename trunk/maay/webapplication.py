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
#from xmlrpclib import ServerProxy
from itertools import cycle
from tempfile import mkdtemp
import os, os.path as osp

from zope.interface import Interface
from twisted.web import static
from twisted.web.xmlrpc import Proxy
from twisted.internet import reactor
from nevow import rend, tags, loaders

from logilab.common.textutils import normalize_text

from maay.querier import WEB_AVATARID
from maay.configuration import get_path_of, IndexerConfiguration
from maay.texttool import makeAbstract, WORDS_RGX, normalizeText, boldifyText
from maay.query import Query
from maay.p2pquerier import P2pQuerier, P2pQuery
from maay.dbentity import Document
import maay.indexer

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
        print "Rendering error msg", self.msg
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

class DownloadedDocs:
    """manage automatic removal of locally downloaded
       documents in a clunky way
       note : tmpdirs should contain exactly one file
              and last no longer than the file
    """
    
    DIRS = {}

    def makeTmpDir():
        tempdir = mkdtemp()
        DownloadedDocs.DIRS[tempdir] = []
        print "DownaloadedDocs makeTmpDir : created %s" % tempdir
        return tempdir
    makeTmpDir = staticmethod(makeTmpDir)

    def addFile(tempdir, thefile):
        DownloadedDocs.DIRS[tempdir].append(thefile)
        print "DownaloadedDocs makeTmpDir : added %s to %s" \
              % (osp.basename(thefile), tempdir)
        reactor.callLater(30, DownloadedDocs.cleanup)
    addFile = staticmethod(addFile)

    def cleanup():
        for tmpdir in DownloadedDocs.DIRS:
            files = DownloadedDocs.DIRS[tmpdir]
            for fil in files:
                try:
                    os.unlink(fil)
                    print "DownloadedDocs cleanup : removing %s" % fil
                except:
                    import traceback
                    traceback.print_exc()
            try:
                os.rmdir(tmpdir)
                print "DownloadedDocs cleanup : removing %s" % tmpdir
            except:
                import traceback
                traceback.print_exc()
    cleanup = staticmethod(cleanup)
                    
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
        print "I HOPE WE NEVER GET THERE"
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
        words = context.arg('words').split()
        filename = context.arg('filename')
        docid = context.arg('docid')
        if not host or not port or not docid:
            return Maay404()
        print "SearchForm distantfile"
        proxy = Proxy('http://%s:%s' % (host, port))
        d = proxy.callRemote('downloadFile', docid, words)
        d.addCallback(self.gotDataBack, filename)
        d.addErrback(self.onDownloadFileError, filename)
        return d

    def gotDataBack(self, rpcFriendlyData, filename):
        fileData = rpcFriendlyData.data
        print " ... downloaded !"
        tmpdir = DownloadedDocs.makeTmpDir()
        filepath = osp.join(tmpdir, filename)
        f=file(filepath,'wb')
        f.write(fileData)
        f.close()
        return DistantFilePage(tmpdir, filepath)

    def onDownloadFileError(self, error, filename):
        msg = "Error while downloading file: %s" % (filename,)
        return Maay404(msg)
    
class DistantFilePage(static.File):
    def __init__(self, tmpdir, filepath):
        static.File.__init__(self, filepath)
        self.tmpdir = tmpdir
        self.filepath = filepath
        
    def __del__(self):
        DownloadedDocs.addFile(self.tmpdir, self.filepath)
    

class IndexationPage(MaayPage):
    # just for the demo. Should be moved to a adminpanel interface later.
    """index page"""
    bodyFactory = loaders.xmlfile(get_path_of('indexationpage.html'))
    addSlash = False
    
    def __init__(self, msg = "No message"):
        MaayPage.__init__(self)
        self._msg = msg
        self.indexerConfig = IndexerConfiguration()
        self.indexerConfig.load()

    def render_message(self, context, data):
        return self._msg

    def data_indexedprivatedirectories(self, context, data):
        if not self.indexerConfig.private_index_dir:
            return ["No indexed private directory."]
        return self.indexerConfig.private_index_dir

    def data_skippedprivatedirectories(self, context, data):
        if not self.indexerConfig.private_skip_dir:
            return ["No skipped private directory."]
        return self.indexerConfig.private_skip_dir

    def data_indexedpublicdirectories(self, context, data):
        if not self.indexerConfig.private_skip_dir:
            return ["No indexed public directory."]
        return self.indexerConfig.public_index_dir

    def data_skippedpublicdirectories(self, context, data):
        if not self.indexerConfig.public_skip_dir:
            return ["No skipped public directory."]
        return self.indexerConfig.public_skip_dir


    def render_directory(self, context, name):
        print "directory = %s" % name
        context.fillSlots("name", name)
        return context.tag

class ResultsPageMixIn:

    def data_results(self, context, data):
        return self.results
    
    def macro_footer(self, context):
        return loaders.xmlfile(get_path_of('footer.html'))

    def macro_prevnext(self, context):
        return loaders.stan(
          tags.invisible()[
            tags.invisible(render=tags.directive("onFirstSlice"))[
              tags.invisible(pattern="Previous")[
                tags.a(href=tags.invisible(render=self.prevset_url))['Previous'],
                tags.xml(" &nbsp; "),
                ],
              ],
            tags.invisible(render=tags.directive("onLastSlice"))[
              tags.a(pattern="Next", href=tags.invisible(render=self.nextset_url))['Next']
            ],
          ],
        )

    def render_onLastSlice(self, context, data):
        """returns a specific pattern to tell if we're on last slice or not"""
        q = inevow.IQ(context)
        nextPattern = q.onePattern('Next')
        localCount, distantCount = self.querier.countResults(self.queryId)
        if self.onlyDistant:
            resultsCount = distantCount
        elif self.onlyLocal:
            resultsCount = localCount
        else:
            resultsCount = localCount + distantCount
        offset = self.query.offset
        if (offset + 15) > resultsCount:
            return context.tag().clear()
        return nextPattern or context.tag().clear()

    def render_onFirstSlice(self, context, data):
        """returns a specific pattern to tell if we're on first slice or not"""
        q = inevow.IQ(context)
        falsePattern = q.onePattern('Previous')
        if (self.query.offset <= 0):
            return context.tag().clear()
        return falsePattern or context.tag().clear()
    
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
        context.fillSlots('start_result', offset + 1)
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

    def nextset_url(self, context, data):
        return 'javascript: browseResults(%s);' % (self.query.offset + 15,)

    def prevset_url(self, context, data):
        offset = self.query.offset
        if offset:
            offset -= 15
        return 'javascript: browseResults(%s);' % (offset,)

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
        context.fillSlots('docid', document.document_id)
        context.fillSlots('docurl', tags.xml(boldifyText(document.url, words)))
        context.fillSlots('words', self.query.joinwords(' ')) #WORDS
        context.fillSlots('readable_size', document.readable_size())
        date = datetime.fromtimestamp(document.publication_time)
        context.fillSlots('publication_date', date.strftime('%d %b %Y'))
        return context.tag
    
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
            results = querier.findDocuments(self.query)
            webappConfig = INodeConfiguration(context)
            p2pQuery = P2pQuery(webappConfig.get_node_id(),
                                webappConfig.rpcserver_port,
                                self.query)
            self.queryId = p2pQuery.qid
            self.p2pQuery = p2pQuery
            self.querier.pushDocuments(self.queryId, results, provider=None)
            self.results = self.querier.getQueryResults(self.queryId, offset=0)
            
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
    docFactory = loaders.xmlstr("""
  <div id="resultsDiv" xmlns="http://www.w3.org/1999/xhtml" xmlns:nevow="http://nevow.com/ns/nevow/0.1" >
   <div class="message" nevow:render="title">Results <b><nevow:slot name="start_result" /></b> - <b><nevow:slot name="end_result" /></b> of <b><nevow:slot name="count" /></b> for <b><nevow:slot name="words" /></b>.</div>
    <div class="prevnext"><nevow:invisible nevow:macro="prevnext" /></div>
   <table>
     <tr>
       <td><div class="localPublicResult"><a href="javascript: onlyLocalResults();"><span nevow:render="localcount" /> local</a></div></td>
       <td> - </td>
       <td> <div class="distantResult"><a href="javascript: onlyDistantResults();"><span nevow:render="distantcount" /> distant</a></div></td>
       <td>-</td>
       <td><a href="javascript: allResults();"><span nevow:render="totalcount" /> all</a></td>
     </tr>
   </table>
    <table class="results" nevow:render="sequence" nevow:data="results">
      <tr nevow:pattern="item" nevow:render="row">
        <td>
          <div>
            <nevow:attr name="class"><nevow:slot name="resultClass" /></nevow:attr>
            <table>
              <tr><td><div><nevow:attr name="class"><nevow:slot name="mime_type"/></nevow:attr></div></td>
                  <td>
                   <a><nevow:attr name="class"><nevow:slot name="linkClass" /></nevow:attr>
                    <nevow:attr name="href"><nevow:slot name="url" /></nevow:attr>
                    <nevow:slot name="doctitle">DOC TITLE</nevow:slot>
                   </a>
                  </td>
              </tr>
            </table>
            <div class="resultDesc"><nevow:slot name="abstract" /></div>
            <span class="resultUrl"><span nevow:render="peer" /><nevow:slot name="docurl" /> - <nevow:slot name="readable_size" /> - <nevow:slot name="publication_date" /></span>
          </div>
        </td>
      </tr>
    </table>
    <div class="prevnext"><nevow:invisible nevow:macro="prevnext" /></div>
    <nevow:invisble nevow:macro="footer" />
  </div>
    """)
    
    def __init__(self, results, querier, query, queryId,
                 onlyLocal=False, onlyDistant=False):
        self.results = results
        self.querier = querier
        self.query = query
        self.queryId = queryId
        self.onlyLocal = onlyLocal
        self.onlyDistant = onlyDistant

    def render_peer(self, context, data):
        """:type data: Result"""
        if data.login is None:
            return ''
        return '%s (%s) - ' % (data.login, data.host)
    
    def render_row(self, context, data):
        document = data
        ResultsPageMixIn.render_row(self, context, data)
        if document.host == 'localhost':
            baseurl = '/download?docid=%s' % (document.document_id,)
            context.fillSlots('linkClass', "docTitle")
            # TODO: make a difference between private and public results
            context.fillSlots('resultClass', "localPublicResult")
        else:
            baseurl = '/distantfile?docid=%s' % (document.document_id,)
            context.fillSlots('linkClass', "distantDocTitle")
            context.fillSlots('resultClass', "distantResult")
            baseurl += '&host=%s' % (document.host,)
            baseurl += '&port=%s' % (document.port,)
        baseurl += '&filename=%s' % osp.basename(document.url)
        baseurl += '&words=%s' % '+'.join(self.query.words)
        context.fillSlots('url', baseurl)
        return context.tag

    def render_nextset_url(self, context, data):
        return 'javascript: browseResults(%s);' % (self.query.offset + 15,)

    def render_prevset_url(self, context, data):
        offset = self.query.offset
        if offset:
            offset -= 15
        return 'javascript: browseResults(%s);' % (offset,)


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
