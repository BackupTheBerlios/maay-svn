"""
  This module contains the functions used for the web user interface.
  First attempt to replace the homemade template engine to Cheetah.
"""

import os
import stat
import sys
import time

import re
import thread
import urlparse
import urllib
import cgi
import Cookie
import gc
import urllib
import mimetypes

import Cheetah
import Cheetah.Template

import tools
import constants
import resultspool
import converter.texttohtml
import converter.htmltomaayhtml
import converter.htmltools
import maay.datastructure.documentinfo

import maay.config.language
import globalvars

current_result_spool_query_id = -1

MAAY_SCRIPT_PREFIX = "maay"

def __cut_str(u, s):
    if len(u) < s:
        return u
    else:
        return "%s..." % u[:s - 3]

#TODO: rajouter ce menu dans le template
#       if globalvars.localAuthentification == 1 or client_ip != '127.0.0.1':
#               menus.append((LOGOUT_MENU, globalvars.language.getValue('MENU_LOGOUT'), '/maay/logout'))

def __get_documents_cheetah(httpRequestHandler, selected_document_state):
    documentInfos = globalvars.database.getDocumentInfos(search_range = selected_document_state)
    dict = {
             'selected_document_state': selected_document_state,
             'documentInfos': documentInfos}
    obj = globalvars
    template_file = open("config/templates/documents.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_document_info_cheetah(httpRequestHandler, document_id):
    documentInfo = globalvars.database.getDocumentInfo(document_id)
    fileInfos = globalvars.database.getFileInfos(db_document_id=documentInfo.db_document_id)
    documentProviders = globalvars.database.getDocumentProviders(documentInfo.db_document_id)

    documentScores = globalvars.database.getDocumentScores(db_document_id=documentInfo.db_document_id, order="download_count")

    dict = {
             'documentInfo': documentInfo,
             'fileInfos': fileInfos,
             'documentProviders': documentProviders,
             'documentScores': documentScores
            }
    obj = globalvars
    template_file = open("config/templates/documentinfo.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_word_info_cheetah(httpRequestHandler, word):
    wordInfo = globalvars.database.getWordInfo(word)
    nodeInterests = globalvars.database.getNodeInterests(words=[word])
    dict = {
            'wordInfo': wordInfo,
            'nodeInterests': nodeInterests
            }
    obj = globalvars
    template_file = open("config/templates/wordinfo.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_node_info_cheetah(httpRequestHandler, node_id):
    nodeInfo = globalvars.database.getNodeInfo(node_id)
    nodeInterests = globalvars.database.getNodeInterests(node_id=node_id)
    dict = {
            'nodeInfo': nodeInfo,
            'nodeInterests': nodeInterests
            }
    obj = globalvars
    template_file = open("config/templates/nodeinfo.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_nodes_cheetah(httpRequestHandler):
    nodeInfos = globalvars.database.getNodeInfos()
    dict = {
            'nodeInfos': nodeInfos
            }
    obj = globalvars
    template_file = open("config/templates/nodes.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_words_cheetah(httpRequestHandler):
    wordInfos = globalvars.database.getWordInfos()
    dict = {
            'wordInfos': wordInfos
            }
    obj = globalvars
    template_file = open("config/templates/words.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_preference_security_cheetah(httpRequestHandler, args):
    comment = ""
    if args.get('changesetting'):
        remoteaccess = args.get('remoteaccess') and args.get('remoteaccess')[0]
        if remoteaccess:
            globalvars.remoteAccess = 1
        else:
            globalvars.remoteAccess = 0
            
        globalvars.config.setValue("RemoteAccess", globalvars.remoteAccess)

        localauth = args.get('localauth') and args.get('localauth')[0]
        if localauth:
            globalvars.sessionID = tools.generate_id()
            headers = [("Set-Cookie", "sessionID=%s" % globalvars.sessionID)]
            globalvars.localAuthentification = 1
        else:
            globalvars.localAuthentification = 0
        globalvars.config.setValue("LocalAuthentification", globalvars.localAuthentification)

        comment = "Settings changed !"

    elif args.get('changeauth'):
        password = args.get('password')[0]
        newlogin = args.get('newlogin') and args.get('newlogin')[0]
        newpassword1 = args.get('newpassword1') and args.get('newpassword1')[0]
        newpassword2 = args.get('newpassword2') and args.get('newpassword2')[0]
        globalvars.logger
        
        if password == globalvars.password:
            if newpassword1 == newpassword2:
                comment = "Password changed !"
                globalvars.login = newlogin
                globalvars.password = newpassword1
                globalvars.config.setValue('Login', newlogin)
                globalvars.config.setValue('Password', newpassword1)
                globalvars.config.save()
            else:
                comment = "New passwords do not match !"

        else:
            comment = "Bad password !"
            
    dict = {
            'comment': comment,
            }
    obj = globalvars
    template_file = open("config/templates/prefsecurity.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_preference_indexation_cheetah(httpRequestHandler, args):
    comment = ""
    if args.get('save'):
        indexedDirectoriesStr = args.get('indexedDirectories') and args.get('indexedDirectories')[0]
        notIndexedDirectoriesStr = args.get('notIndexedDirectories') and args.get('notIndexedDirectories')[0]

        if indexedDirectoriesStr:
            indexedDirectories = indexedDirectoriesStr.split("\r\n")
            tools.remove_void_entries(indexedDirectories)
            indexedDirectories.sort()
        else:
            indexedDirectories = []
            
        if notIndexedDirectoriesStr:
            notIndexedDirectories = notIndexedDirectoriesStr.split("\r\n")
            tools.remove_void_entries(notIndexedDirectories)
            notIndexedDirectories.sort()
        else:
            notIndexedDirectories = []
    
        globalvars.indexer.setIndexedDirectories(indexedDirectories)
        globalvars.indexer.setNotIndexedDirectories(notIndexedDirectories)
        globalvars.indexer.forcePrivateReindexationWhenFinished()
        
        
        print "index = %s" % str(indexedDirectories)
        print "not index = %s" % str(notIndexedDirectories)

        publishedDirectoriesStr = args.get('publishedDirectories') and args.get('publishedDirectories')[0]
        notPublishedDirectoriesStr = args.get('notPublishedDirectories') and args.get('notPublishedDirectories')[0]

        if publishedDirectoriesStr:
            publishedDirectories = publishedDirectoriesStr.split("\r\n")
            tools.remove_void_entries(publishedDirectories)
            publishedDirectories.sort()
        else:
            publishedDirectories = []
            
        if notPublishedDirectoriesStr:
            notPublishedDirectories = notPublishedDirectoriesStr.split("\r\n")
            tools.remove_void_entries(notPublishedDirectories)
            notPublishedDirectories.sort()
        else:
            notPublishedDirectories = []
    
        globalvars.indexer.setPublishedDirectories(publishedDirectories)
        globalvars.indexer.setNotPublishedDirectories(notPublishedDirectories)
        globalvars.indexer.forcePublishedReindexationWhenFinished()

        comment = "Indexation rules saved !"
        
        maay.globalvars.config.setValue('LastIndexedPrivateFilename', maay.globalvars.indexer.getLastIndexedPrivateFilename())
        maay.globalvars.config.setValue('IndexedDirectory', maay.globalvars.indexer.getIndexedDirectories())
        maay.globalvars.config.setValue('NotIndexedDirectory', maay.globalvars.indexer.getNotIndexedDirectories())
        maay.globalvars.config.setValue('PublishedDirectory', maay.globalvars.indexer.getPublishedDirectories())
        maay.globalvars.config.setValue('NotPublishedDirectory', maay.globalvars.indexer.getNotPublishedDirectories())

        globalvars.config.save()


    dict = {
            'comment': comment,
            'publishedDirectories': tools.seq2lines(globalvars.indexer.getPublishedDirectories()),
            'notPublishedDirectories': tools.seq2lines(globalvars.indexer.getNotPublishedDirectories()),
            'indexedDirectories': tools.seq2lines(globalvars.indexer.getIndexedDirectories()),
            'notIndexedDirectories': tools.seq2lines(globalvars.indexer.getNotIndexedDirectories()),
            }
    obj = globalvars
    template_file = open("config/templates/prefindexation.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_preference_ui_cheetah(httpRequestHandler, args):
    comment = ""
    if args.get('rs'):
        rs = int(args.get('rs')[0])
        if rs in (10, 20, 50, 100):
            globalvars.result_count_per_page = rs
            globalvars.config.setValue("ResultPerPage", globalvars.result_count_per_page)
            comment = "Result count per page set to %s" % rs
    elif args.get('lang'):
        lang = args.get('lang')[0]
        globalvars.language.setLanguage(lang)
        comment = "Language set to %s" % lang


    dict = {'comment': comment}
    obj = globalvars
    template_file = open("config/templates/prefui.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_preference_debug_cheetah(httpRequestHandler, args):
    comment = ""

    if args.get('repository'):
        globalvars.taskScheduler.force_task("indexer")
        comment = "Full indexing started"
    elif args.get('affinity'):
        globalvars.taskScheduler.force_task("affinity")
        comment = "Affinity computation started"
    elif args.get('matching'):
        globalvars.taskScheduler.force_task("matching")
        comment = "Matching computation started"
    elif args.get('idxpr'):
        idxpr = int(args.get('idxpr')[0])
        if idxpr == constants.LOW_PRIORITY:
            comment = "Indexation priority set to low"
            globalvars.indexer.setPriority(constants.LOW_PRIORITY)
        elif idxpr == constants.MEDIUM_PRIORITY:
            comment = "Indexation priority set to medium"
            globalvars.indexer.setPriority(constants.MEDIUM_PRIORITY)
        elif idxpr == constants.HIGH_PRIORITY:
            comment = "Indexation priority set to high"
            globalvars.indexer.setPriority(constants.HIGH_PRIORITY)
    elif args.get('mode'):
        mode = args.get('mode')[0]
        if mode == 'user':
            globalvars.mode = constants.USER_MODE
            comment = "Mode set to user mode"
        else:
            globalvars.mode = constants.DEVELOPPER_MODE
            comment = "Mode set to developper mode"
        globalvars.config.setValue("Mode", globalvars.mode)
    elif args.get('pubrepository'):
        globalvars.indexer.forcePublishedIndexation()
        comment = "Published repository reindexation started"
    elif args.get('prirepository'):
        globalvars.indexer.forcePrivateIndexation()
        comment = "Published repository reindexation started"


    dict = {
            "comment": comment,
            "priority": globalvars.indexer.getPriority(),
            'publishedIndexationState': ((not globalvars.indexer.isPublishedIndexationFinished()) and "indexing...") or "finished",
            'privateIndexationState': ((not globalvars.indexer.isPrivateIndexationFinished()) and "indexing...") or "finished",
            }
    obj = globalvars
    template_file = open("config/templates/prefdebug.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_results_cheetah(httpRequestHandler, query_id, page = 1, sort_policy = resultspool.SCORE_SORTED, search_range = constants.ALL_SEARCH_RANGE):
    global current_result_spool_query_id

    # find the query ID of the current search tab
    if query_id == -1:
        if current_result_spool_query_id == -1:
            resultSpools = globalvars.maay_core.getResultSpoolManager().getResultSpools()
            if len(resultSpools) > 0:
                current_result_spool_query_id = resultSpools[0].getQueryID()
        query_id = current_result_spool_query_id
    else:
        current_result_spool_query_id = query_id

    if not query_id:
        queryStr = ""
    else:
        resultSpool = globalvars.maay_core.getResultSpoolManager().getResultSpool(query_id)
        if resultSpool:
            queryStr = resultSpool.getLabel()
        else:
            queryStr = ""

    wordsQuery = ""
    documentIDQuery = ""
    urlQuery = ""

    startResult = 0
    endResult = 0

    results = []
    result_count = 0
    
    if resultSpool:
        resultSpool.updateFilteredResultCount()
        for w in resultSpool.getQuery():
            if w[0] == '#':
                documentIDQuery = w[1:]
            elif w.find('url:') == 0:
                urlQuery = w[len('url:'):]
            else:
                wordsQuery += " " + w
        wordsQuery = wordsQuery[1:]

        if resultSpool.getRange() in (constants.INTERNET_SEARCH_RANGE, constants.INTRANET_SEARCH_RANGE):
            startResult = min(resultSpool.getResultCount(), (page - 1) * globalvars.result_count_per_page + 1)
            endResult = min(resultSpool.getFilteredResultCount(search_range), page * globalvars.result_count_per_page)
            result_count = resultSpool.getFilteredResultCount()

            results = resultSpool.getResults(sort_policy)[startResult - 1:endResult]
        else:
            result_count = resultSpool.getResultCount()
            startResult = min(resultSpool.getFilteredResultCount(search_range), (page - 1) * globalvars.result_count_per_page + 1)
            endResult = min(resultSpool.getFilteredResultCount(search_range), page * globalvars.result_count_per_page)

            results = resultSpool.getFilteredResults(search_range_filter=search_range, sort_policy=sort_policy)[startResult - 1:endResult]

    resultSpools = globalvars.maay_core.getResultSpoolManager().getResultSpoolsByNodeID(globalvars.maay_core.getNodeID())

    page_count = int((result_count - 1) / globalvars.result_count_per_page)  + 1

    dict = {
            'queryStr': queryStr,
            'query_id': query_id,
            'wordsQuery': wordsQuery,
            'documentIDQuery': documentIDQuery,
            'urlQuery': urlQuery,
            'resultSpools': resultSpools,
            'start_result': startResult,
            'end_result': endResult,
            'search_range': search_range,
            'result_count': result_count,
            'page': page,
            'page_count': page_count,
            'results': results,
            }
    obj = globalvars
    template_file = open("config/templates/resultspool.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()



def __get_about(httpRequestHandler):
    dict = {}
    obj = globalvars
    template_file = open("config/templates/about.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()


def __get_system(httpRequestHandler, action = None):
    dict = {
                    'node_id':globalvars.maay_core.getNodeID(),
                    'ip':globalvars.ip,
                    'port':globalvars.config.getValue('Port'),
                    'processor_load': "%02d%%" % globalvars.systemMonitor.getProcessorLoad(),
                    'available_memory': globalvars.systemMonitor.getAvailableMemory(),
                    'private_document_count': globalvars.database.getDocumentCount(maay.datastructure.documentinfo.PRIVATE_STATE),
                    'private_document_size': tools.size_str(globalvars.database.getDocumentSizeSum(maay.datastructure.documentinfo.PRIVATE_STATE)),
                    'published_document_count': globalvars.database.getDocumentCount(maay.datastructure.documentinfo.PUBLISHED_STATE),
                    'published_document_size': globalvars.database.getDocumentSizeSum(maay.datastructure.documentinfo.PUBLISHED_STATE),
                    'cached_document_count': globalvars.database.getDocumentCount(maay.datastructure.documentinfo.CACHED_STATE),
                    'cached_document_size': globalvars.database.getDocumentSizeSum(maay.datastructure.documentinfo.CACHED_STATE),
                    'known_document_count': globalvars.database.getDocumentCount(maay.datastructure.documentinfo.KNOWN_STATE),
                    'neighbor_count': globalvars.database.getNodeInfoCount()

            }
    obj = globalvars
    template_file = open("config/templates/system.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()


def __get_document_text(httpRequestHandler, document_id):
    httpRequestHandler.send_response(200)
    httpRequestHandler.send_header('Mime-Type', "text/plain")
    httpRequestHandler.end_headers()
    documentInfo = globalvars.database.getDocumentInfo(document_id)
    httpRequestHandler.wfile.write(documentInfo.text)
    
def __get_document_by_id(httpRequestHandler, document_id, query_id=-1, remote=False):
    if query_id == -1:
        search_query = []
    else:
        resultSpool = globalvars.maay_core.getResultSpoolManager().getResultSpool(query_id)
        if resultSpool:
            search_query = resultSpool.getQuery()
        else:
            search_query = []
    documentInfo = globalvars.database.getDocumentInfo(document_id)

    if not documentInfo:
        print "document not known, send search request on the document id"
        if not documentInfo:
            documentInfo = maay.datastructure.documentinfo.DocumentInfo(None, document_id, "", "", 0, "", 0, maay.datastructure.documentinfo.UNKNOWN_STATE, 0, "", 0)
            globalvars.database.insertDocumentInfo(documentInfo)

        print "send download"
        globalvars.maay_core.send_download_request(document_id, search_query)
        get_download_info(httpRequestHandler, documentInfo, query_id, remote)
    else:
        fileInfos = globalvars.database.getFileInfos(db_document_id = documentInfo.db_document_id)
        fileInfo = None
        for f in fileInfos:
            try:
                print "file : %s" % f.file_name
                os.stat(f.file_name)
                fileInfo = f
                break
            except Exception, e:
                print "file deleted : %s" % f.file_name
                print "exception : %s" % e
                globalvars.database.deleteFileInfo(f.file_name)
                
        globalvars.indexer.checkDocumentState(documentInfo.db_document_id)

        if fileInfo:
            __get_document_by_filename(httpRequestHandler, fileInfo.file_name, document_id=document_id, query_id=query_id)
            globalvars.maay_core.hasDownloaded(globalvars.maay_core.getNodeID(), document_id, search_query, weight=constants.DOWNLOAD_SCORE_WEIGHT)
            if documentInfo.state in (maay.datastructure.documentinfo.KNOWN_STATE, maay.datastructure.documentinfo.UNKNOWN_STATE):
                globalvars.indexer.addNewDocumentToIndex(fileInfo.file_name)


            return
            
        documentInfo.state = maay.datastructure.documentinfo.KNOWN_STATE
        globalvars.database.updateDocumentInfo(documentInfo)

        globalvars.maay_core.send_download_request(document_id, search_query)
        __get_download_info(httpRequestHandler, documentInfo, query_id, remote)

def __display_error_page(httpRequestHandler, code, title, error_title, description):
    httpRequestHandler.send_response(code)
    httpRequestHandler.end_headers()
    dict = {
                    'title':title,
                    'error_title':error_title,
                    'description':description
            }

    obj = globalvars
    template_file = open("config/templates/errorpage.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()


def __get_download_info(httpRequestHandler, documentInfo, query_id, remote=False):
    download = globalvars.downloadManager.getDownload(documentInfo.document_id)
    dict = {
            'download': download,
            'query_id': query_id
            }
    obj = globalvars
    template_file = open("config/templates/downloadinfo.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_document_by_filename(httpRequestHandler, filename, document_id = None, query_id = None):
    try:
        filename = urllib.unquote(filename)
        mode = os.stat(filename)[stat.ST_MODE]
        if stat.S_ISDIR(mode):
            filename = os.path.normpath(filename + "/index.html")

        mime_type = mimetypes.guess_type(filename)

        # check if we can access the file and it exists

        documentInfo = None
        if document_id:
            documentInfo = globalvars.database.getDocumentInfo(document_id=document_id)
    
        if documentInfo and documentInfo.mime_type == 'text/html' and documentInfo.url and documentInfo.state in (maay.datastructure.documentinfo.CACHED_STATE, maay.datastructure.documentinfo.KNOWN_STATE):
            httpRequestHandler.send_response(200)
            httpRequestHandler.send_header('Content-Type', documentInfo.mime_type)
            httpRequestHandler.send_header('Connection', 'close')
            httpRequestHandler.send_header('Accept-Ranges', 'bytes')
            httpRequestHandler.end_headers()

            httpRequestHandler.wfile.write(maay.globalvars.templateFile.getTemplateValue("cached_header", 
            {'documentID' : document_id,
            'queryID' : query_id,
            'url' : documentInfo.url,
            'quotedUrl' : urllib.quote(documentInfo.url),
            'date' : tools.long_date_str(documentInfo.publication_time)
            }))


            fd = open(filename, 'rb')
            converter.htmltomaayhtml.htmlToMaayHtml(document_id, fd, httpRequestHandler.wfile, documentInfo.url)
            fd.close()
            return  

        httpRequestHandler.send_response(200)
        httpRequestHandler.send_header('Content-Type', mime_type)
        httpRequestHandler.send_header('Connection', 'close')
        file_length = os.stat(filename)[stat.ST_SIZE]
        httpRequestHandler.send_header('Content-Length', file_length)
        httpRequestHandler.send_header('Accept-Ranges', 'bytes')

        httpRequestHandler.end_headers()

        fd = open(filename, 'rb')
        while 1:
            buf = fd.read(1024)
            if not buf:
                break
            httpRequestHandler.wfile.write(buf)
        fd.close()

    except:
        globalvars.logger.exception("")
        __display_error_page(httpRequestHandler, 404, "Error 404: Page not found", "Not found", "The requested URL %s was not found on this server" % httpRequestHandler.path)

def __get_excerpt(text, pos, excerpt_half_size=constants.EXCERPT_HALF_SIZE, dot=False):
    if pos >= constants.MAX_TEXT_CONTENT_STORED_SIZE:
        pos = 0
    start = max(0, pos - excerpt_half_size)
    if start > 0:
#               print "text = %s" % text
#               print "start = %s %s %s" % (start, end, pos)
        while start < pos and text[start] != ' ':
            start += 1
        start += 1

    end = min(len(text), start + excerpt_half_size * 2)

    if end < len(text):
        while end > pos and text[end] != ' ':
            end -= 1

    r = text[start:end + 1]
    if dot:
        if start > 0:
            r = "...%s" % r
        if end < len(text):
            r = "%s..." % r
    return r

def __get_versions_cheetah(httpRequestHandler, url, query_id):
    dict = {
                    'url': url,
                    'query_id': query_id
            }

    obj = globalvars
    template_file = open("config/templates/versions.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()

def __get_downloads(httpRequestHandler):
    dict = {
                    'downloads': globalvars.downloadManager.getDownloads()
            }

    obj = globalvars
    template_file = open("config/templates/downloads.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()


def __putInBold(str, words):
    for word in words:
#               pattern = "(^| |,|;|!|\?|<|>|\.)(" + word + ")($| |,|;|!|\?|<|>|\.)"
#               pattern = "(^|\W+)(%s)($|\W+)" % globalvars.accent.extendsMatchingPattern(word)
        pattern = "(%s)" % globalvars.accent.extendsMatchingPattern(word)

        p = re.compile(pattern)
        str = p.sub("<b>\g<1></b>", str)

    return str

def __mergeExcerpts(documentInfo, ds, words, excerpt_half_size = constants.EXCERPT_HALF_SIZE):
    documentScores = []
    for d in ds:
        if d.word in words:
            documentScores.append(d)

    documentScores.sort(lambda x, y: int(x.position - y.position))

    str = ""
    lastEndPosition = 0

    for documentScore in documentScores:
        excerpt = __get_excerpt(documentInfo.text, documentScore.position, excerpt_half_size=excerpt_half_size)
#               excerpt = documentScore.excerpt
        if not excerpt or excerpt == "":
            continue

        # todo: check for accented text
        m = re.search("(^|\W+)(%s)(\W+|$|:)" % documentScore.word, excerpt, re.IGNORECASE)

        if not m or documentScore.position == -1:
            str += excerpt
            endPosition = len(excerpt)
        else:
            pos = m.start()

            startPosition = documentScore.position - pos
            endPosition = len(excerpt) - pos + documentScore.position 

            if startPosition <= lastEndPosition:
                str += converter.texttohtml.textToHTML(excerpt[pos - (documentScore.position - lastEndPosition):])
            else:
                if documentScore.position - excerpt_half_size > 0:
                    str += "<b>...</b>"
                str += converter.texttohtml.textToHTML(excerpt)

        lastEndPosition = endPosition

    if not str:
        return None
        
    str += " <b>...</b>"
    return str


def __close_result_spool(httpRequestHandler, query_id):
    global current_result_spool_query_id
    resultSpools = globalvars.maay_core.getResultSpoolManager().getResultSpoolsByNodeID(globalvars.maay_core.getNodeID())
    removedResultSpool = globalvars.maay_core.getResultSpoolManager().getResultSpool(query_id)

    try:
        index = resultSpools.index(removedResultSpool)
    except ValueError:
        index = -1

#       print "index = %s" % index

    globalvars.maay_core.getResultSpoolManager().removeResultSpool(removedResultSpool)

    if query_id == current_result_spool_query_id:
        if index >= len(resultSpools) - 1:
            index = len(resultSpools) - 1

        if index == -1:
            current_result_spool_query_id = None
        else:
            current_result_spool_query_id = resultSpools[index].getQueryID()



def __send_search_query(httpRequestHandler, query, search_range, result_count, query_id = None):
    if not query_id:
        query_id = globalvars.maay_core.send_search_request(query, constants.INIT_TTL, search_range, constants.MIN_SCORE, constants.INIT_FNC, result_count)
    return query_id



def __get_maayify_url(httpRequestHandler, url=None, title = None, keywords=None, submit=0):
    if submit:
        dict = {}
        obj = globalvars
        template_file = open("config/templates/maayifyclose.tmpl", "r")
        t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
        httpRequestHandler.wfile.write(str(t))
        template_file.close()

        globalvars.urlindexer.insertURL(url, keywords, weight=constants.ANNOTATION_SCORE_WEIGHT)
    else:
        dict = {
                'title': title,
                'url': url,
                }

        obj = globalvars
        template_file = open("config/templates/maayifyurl.tmpl", "r")
        t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
        httpRequestHandler.wfile.write(str(t))
        template_file.close()

def __get_maayify_document(httpRequestHandler, document_id=None, title = None, keywords=None, submit=0):
    if submit:
        dict = {}
        obj = globalvars
        template_file = open("config/templates/maayifyclose.tmpl", "r")
        t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
        httpRequestHandler.wfile.write(str(t))
        template_file.close()


        globalvars.maay_core.hasDownloaded(globalvars.maay_core.getNodeID(), document_id, keywords, weight=constants.ANNOTATION_SCORE_WEIGHT)
    else:
        documentInfo = globalvars.database.getDocumentInfo(document_id=document_id)
        dict = {
                 'documentInfo': documentInfo
                }
        obj = globalvars
        template_file = open("config/templates/maayifydoc.tmpl", "r")
        t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
        httpRequestHandler.wfile.write(str(t))
        template_file.close()


class LogReader:
    def __init__(self, fd):
        self.__level = 'INFO'
        self.__fd = fd
        self.__finished = 0
        self.next = self._next().next

    def _next(self):
        """ return read line """
        if not self.__finished:
            while True:
                line = self.__fd.readline()
                if not line:
                    break

                words = line.split(' ', 3)
                if len(words) == 4:
                    date, hour, level_tmp, text = words             
                if level_tmp in ('INFO', 'DEBUG', 'EXCEPTION', 'ERROR'):
                    self.__level = level_tmp
                yield (self.__level, line)
            self.__finished = 1

    def __iter__(self):
        return self._next()



def __get_logs(httpRequestHandler):
    fd = file(os.path.join('logs', 'maay.log'))
    reader = LogReader(fd)
    dict = {'logReader': reader}
    obj = globalvars
    template_file = open("config/templates/logs.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()
    fd.close()



def __get_login_page(httpRequestHandler, url="", comment=""):
    httpRequestHandler.wfile.write(globalvars.templateFile.getTemplateValue("login_page", {'url': url, 'comment': comment}))


def __get_remote_download(httpRequestHandler, document_id, download=None):
    if not download:
        documentInfos = globalvars.database.getDocumentInfos(document_id=document_id)
        documentInfo = documentInfos and documentInfos[0]
        node_id = None
        ip = None
        port = None
        last_providing_time = None
        last_seen_time = None
        
        if documentInfo and documentInfo.state in (maay.datastructure.documentinfo.PUBLISHED_STATE, maay.datastructure.documentinfo.CACHED_STATE):
            node_id = globalvars.maay_core.getNodeID()
            ip = globalvars.ip
            port = globalvars.port
            last_providing_time = int(time.time())
            last_seen_time = int(time.time())
        elif documentInfo:
            documentProviders = globalvars.database.getDocumentProviders(documentInfo.db_document_id)
            documentProvider = len(documentProviders) > 0 and documentProviders[0]
            nodeInfo = globalvars.database.getNodeInfo(documentProvider.node_id)
            
            if documentProvider and nodeInfo:
                node_id = documentProvider.node_id
                ip = nodeInfo.ip
                port = nodeInfo.port
                last_providing_time = documentProvider.last_providing_time
                last_seen_time = nodeInfo.last_seen_time
                
        httpRequestHandler.wfile.write(globalvars.templateFile.getTemplateValue("remote_download_page",
                {
                        'documentID': document_id,
                        'nodeID': node_id,
                        'ip': ip,
                        'port': port,
                        'lastSeenTime': last_seen_time,
                        'lastProvidingTime': last_providing_time

                }))
    else:
        __get_document_by_id(httpRequestHandler, document_id, remote=True)

def __get_help(httpRequestHandler):
    dict = {}
    obj = globalvars
    template_file = open("config/templates/help.tmpl", "r")
    t = Cheetah.Template.Template(file=template_file, searchList=[dict, obj])
    httpRequestHandler.wfile.write(str(t))
    template_file.close()



def __get_maayl(httpRequestHandler):
    httpRequestHandler.wfile.write(globalvars.templateFile.getTemplateValue("maayl_page"))

def handle_get(httpRequestHandler):
    u = urlparse.urlparse(httpRequestHandler.path)
    client_ip, client_port = httpRequestHandler.client_address
    
    # let the / (url format)
    words = u[2].split("/", 2)
    first_directory = None
    if len(words) > 1:
        first_directory = words[1]

    args = cgi.parse_qs(u[4])

    if first_directory == 'maay':
        if len(words) >= 3:
            maay_action = words[2]
        else:
            maay_action = None

        if maay_action != "remotedownload" and client_ip != '127.0.0.1' and globalvars.remoteAccess == 0:
            __display_error_page(httpRequestHandler, 403, "Error 403: Forbidden", "Forbidden", "You do not have the right to access to the URL %s on this server" % httpRequestHandler.path)
            return

        # check that the user is logged, if it is not the case, display login page.
        if maay_action != "remotedownload" and maay_action != 'login':
            if client_ip != '127.0.0.1' or globalvars.localAuthentification == 1:
                c = Cookie.SimpleCookie(httpRequestHandler.headers.get('Cookie'))
                sessionID = None
                if c.has_key("sessionID"):
                    sessionID = c["sessionID"].value
                print "sessions %s / %s" % (sessionID, globalvars.sessionID)
                if not globalvars.sessionID or sessionID != globalvars.sessionID:
                    __get_login_page(httpRequestHandler, httpRequestHandler.path)
                    return                          
        if  maay_action == 'login':
            login = None
            password = None
            try:
                login = args.get('login')[0]
                password = args.get('password')[0]
            except Exception, e:
                pass

            urls = args.get('url')
            url = urls and urls[0]

            if login == globalvars.login and password == globalvars.password:
                if not url:
                    url = "/maay/resultspool"
            
                globalvars.sessionID = tools.generate_id()
                httpRequestHandler.send_response(302)
                httpRequestHandler.send_header("Set-Cookie", "sessionID=%s" % globalvars.sessionID)
                httpRequestHandler.send_header('Location', '%s' % url)
                httpRequestHandler.end_headers()
            else:
                httpRequestHandler.send_response(302)
                __get_login_page(httpRequestHandler, url, "Too bad, try again !")

                httpRequestHandler.end_headers()
        elif  maay_action == 'logs':
            __get_logs(httpRequestHandler)
        elif  maay_action == 'logout':
            httpRequestHandler.send_response(302)
            httpRequestHandler.send_header("Set-Cookie", "sessionID=; max-age=0")
            __get_login_page(httpRequestHandler)
        elif  maay_action == 'canceldownload':
            dids = args.get('did')
            document_id = dids[0]
            download = globalvars.downloadManager.cancelDownload(document_id)
            httpRequestHandler.send_response(302)
            httpRequestHandler.send_header('Location', '/maay/downloads')

        elif  maay_action == 'search':
            qs = args.get('q')
#                       if qs:
#                               qs[0] = qs[0].strip()
            if qs and qs[0]:
                query = qs[0].split()
            else:
                query = []
                
            qids = args.get('qid')
            if qids and qids[0]:
                query_id = qids[0]
                resultSpool = globalvars.maay_core.getResultSpoolManager().getResultSpool(query_id)
                globalvars.maay_core.send_search_request(resultSpool.getQuery(), constants.INIT_TTL, resultSpool.getRange(), constants.MIN_SCORE, constants.INIT_FNC, resultSpool.getExpectedResultCount(), query_id = query_id)
                httpRequestHandler.send_response(302)
                httpRequestHandler.send_header('Location', "/maay/resultspool?qid=%s" % query_id)
                httpRequestHandler.end_headers()
                return

            did = args.get('did')
            if did:
                query.append("#%s" % did[0])
            else:
                document_id = None

            urls = args.get('url')
            if urls:
                query.append("url:%s" % urls[0])
#                               url = urls[0]
            else:
                url = None


            if not query and not document_id and not url:
                httpRequestHandler.send_response(302)
#                               httpRequestHandler.send_header('Location', "http://%s:%s/maay/resultspool" % (host, globalvars.port))
                httpRequestHandler.send_header('Location', "/maay/resultspool")
                httpRequestHandler.end_headers()
                return

    #               print "query = %s" % query
            # number of results expected
            r = args.get('r')
            if r:
                result_count = int(r[0])
            else:
                result_count = globalvars.result_count_per_page

            if args.get('desktopsearch'):
                search_range = constants.DESKTOP_SEARCH_RANGE
                result_count = -1
            elif args.get('privatesearch'):
                search_range = constants.PRIVATE_SEARCH_RANGE
            elif args.get('publishsearch'):
                search_range = constants.PUBLISHED_SEARCH_RANGE
            elif args.get('intranetsearch'):
                search_range = constants.INTRANET_SEARCH_RANGE
            elif args.get('googlesearch'):
                search_range = constants.INTERNET_SEARCH_RANGE
            else:
                search_range = constants.MAAY_SEARCH_RANGE

                        
            query_id = __send_search_query(httpRequestHandler, query, search_range, result_count)
            httpRequestHandler.send_response(302)
#                       httpRequestHandler.send_header('Location', "http://%s:%s/maay/resultspool?qid=%s" % (host, globalvars.port, query_id))
            httpRequestHandler.send_header('Location', "/maay/resultspool?qid=%s" % query_id)
            httpRequestHandler.end_headers()
        elif maay_action == 'doctext':
            document_id = args['did'][0]
            __get_document_text(httpRequestHandler, document_id)
        elif maay_action == 'document':
            # todo: test if d is correct (40 char and only one word)
            document_id = args['did'][0]
            qid = args.get('qid')
            if qid:
                query_id = args['qid'][0]
            else:
                query_id = -1

            nids = args.get('nid')
            node_id = nids and nids[0]

            ips = args.get('ip')
            ip = ips and ips[0]

            ports = args.get('port')
            port = ports and ports[0]
            
            lsts = args.get('lst')
            last_seen_time = lsts and lsts[0]

            lpts = args.get('lpt')
            last_providing_time = lpts and lpts[0]

            if node_id and ip and port and last_seen_time and last_providing_time:
                maay.globalvars.maay_core.updateNodeInfo(node_id, ip, port, 0, 0, last_seen_time)
                documentInfos = globalvars.database.getDocumentInfos(document_id = document_id)
                documentInfo = (len(documentInfos) > 0) and documentInfos[0]
                globalvars.maay_core.updateDocumentProvider(documentInfo.db_document_id, node_id, last_providing_time)

            __get_document_by_id(httpRequestHandler, document_id, query_id)
        elif maay_action == 'documentinfo':
            # TODO: test if d is correct (40 char and only one word)
            document_id = args['did'][0]
            query = []
            __get_document_info_cheetah(httpRequestHandler, document_id)
        elif maay_action == 'resultspool':
            # TODO: test if d is correct (40 char and only one word)
            sm = args.get('sm')
            if sm:
                if sm[0] == '0':
                    globalvars.search_mode = constants.NORMAL_SEARCH_MODE
                elif sm[0] == '1':
                    globalvars.search_mode = constants.ADVANCED_SEARCH_MODE
            qid = args.get('qid')
            if qid:
                query_id = qid[0]
            else:
                query_id = current_result_spool_query_id        
            p = args.get('p')
            if p:
                page=int(p[0])
            else:
                page = 1

            r = args.get('r')
            if r:
                search_range=int(r[0])
            else:
                search_range = constants.ALL_SEARCH_RANGE


            s = args.get('s')
            if s:
                sort_policy = int(s[0])
            else:
                sort_policy = resultspool.SCORE_SORTED

            __get_results_cheetah(httpRequestHandler, query_id, page, sort_policy, search_range)
        elif maay_action == 'closeresultspool':
            # TODO: test if d is correct (40 char and only one word)
            query_id = args['qid'][0]
            __close_result_spool(httpRequestHandler, query_id)
            httpRequestHandler.send_response(302)
            httpRequestHandler.send_header('Location', '/maay/resultspool')

        elif maay_action == 'nodes':
            __get_nodes_cheetah(httpRequestHandler)
        elif maay_action == 'nodeinfo':
            nodeID = args['nid'][0]
            __get_node_info_cheetah(httpRequestHandler, nodeID)
        elif maay_action == 'words':
            __get_words_cheetah(httpRequestHandler)
        elif maay_action == 'wordinfo':
            word = args['w'][0]
            __get_word_info_cheetah(httpRequestHandler, word)
        elif maay_action == 'system':
            __get_system(httpRequestHandler)
        elif maay_action in ('preferences', 'prefsecurity'):
            __get_preference_security_cheetah(httpRequestHandler, args)
        elif maay_action == 'prefindexation':
            __get_preference_indexation_cheetah(httpRequestHandler, args)
        elif maay_action == 'prefui':
            __get_preference_ui_cheetah(httpRequestHandler, args)
        elif maay_action == 'prefdebug':
            __get_preference_debug_cheetah(httpRequestHandler, args)
        elif maay_action == 'documents':
            v = args.get('v')
            if v:
                view = int(v[0])
            else:
                view = maay.datastructure.documentinfo.PUBLISHED_STATE
                
#                       __get_repository(httpRequestHandler, view)
            __get_documents_cheetah(httpRequestHandler, view)
        elif maay_action == 'versions':
            urls = args.get('url')
            if urls:
                url = urls[0]
            qids = args.get('qid')
            if qids:
                query_id = qids[0]
            else:
                query_id = None
            __get_versions_cheetah(httpRequestHandler, url, query_id)
        elif maay_action == 'link':
            did = args.get('did')
            if did:
                document_id = urllib.unquote(did[0])
            else:
                __display_error_page(httpRequestHandler, 200, "Bad arguments 1", "URL = %s" % httpRequestHandler.path)  
                return
            p = args.get('path')
            if p:
                path = p[0]
            else:
                __display_error_page(httpRequestHandler, 200, "Bad arguments 2", "URL = %s" % httpRequestHandler.path)  
                return
            u = args.get('url')
            if u:
                url = urllib.unquote(u[0])
            else:
                url = None

    #               print "document_id = %s" % document_id
    #               print "path = %s" % path
            __get_link(httpRequestHandler, document_id, path, url)

        elif maay_action == 'downloads':
            __get_downloads(httpRequestHandler)

        elif maay_action == 'help':
            __get_help(httpRequestHandler)
        elif maay_action == 'about':
            __get_about(httpRequestHandler)

        elif maay_action == 'url':
#                       __get_url(httpRequestHandler)
            urls = args.get('url')
            qids = args.get('qid')
            url = urls[0]
            query_id = qids[0]
            httpRequestHandler.send_response(302)
            httpRequestHandler.send_header('Location', url)
            httpRequestHandler.end_headers()

            resultSpool = globalvars.maay_core.getResultSpoolManager().getResultSpool(query_id)
            globalvars.urlindexer.insertURL(url, resultSpool.getQuery(), weight=constants.DOWNLOAD_SCORE_WEIGHT)
        elif maay_action == 'remotedownload':
            dids = args.get('did')
            document_id = dids[0]
            downloads = args.get('download')
            download = downloads and downloads[0]
            __get_remote_download(httpRequestHandler, document_id, download)

        elif maay_action == 'redir':
            urls = args.get('url')
            url = urls[0]
            globalvars.command.start(url)
        elif maay_action == 'maayify':
            urls = args.get('url')
            url = urls and urls[0]
            titles = args.get('title')
            print "title = %s" % str(titles)
            title = (titles and titles[0]) or "No title"

            dids = args.get('did')
            document_id = dids and dids[0]
            
            submit = args.get('maayify')
            keywords = None
            if submit:
                kwss = args.get('keywords')
                kws = (kwss and kwss[0]) or ""
                keywords = kws.split()

            if document_id:
                __get_maayify_document(httpRequestHandler, document_id=document_id, keywords=keywords, submit=submit)
            else:
                __get_maayify_url(httpRequestHandler, url=url, title=title, keywords=keywords, submit=submit)
        elif maay_action == 'maayl':
            __get_maayl(httpRequestHandler)
        else:
            # TODO: do an error page
            file_path = os.path.normpath("%s%s%s" % (globalvars.config.getValue("MaayDocumentRoot"), os.path.sep, words[2]))
            __get_document_by_filename(httpRequestHandler, file_path)
    elif first_directory == 'pub':
        print "url = %s" % u[2]
        file_path = os.path.normpath("%s%s%s" % (globalvars.config.getValue("PublishedDocumentRoot"), os.path.sep, words[2]))
        __get_document_by_filename(httpRequestHandler, file_path)
    else:
        file_path = os.path.normpath("%s%s%s" % (globalvars.config.getValue("WWWDocumentRoot"), os.path.sep, u[2]))
        __get_document_by_filename(httpRequestHandler, file_path)


