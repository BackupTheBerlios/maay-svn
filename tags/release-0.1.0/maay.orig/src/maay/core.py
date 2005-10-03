"""Module <core>: Maay Core

This modules contains the description of a maay core class.
It handles event such as :
- handling document score update (after reception of response)
- 
"""

import time
import math
import httplib
import threading

import tools

import constants
import globalvars

import maay.datastructure.nodeinfo
import maay.datastructure.wordinfo
import maay.datastructure.documentscore
import maay.datastructure.nodeinterest
import maay.datastructure.documentprovider
import maay.datastructure.documentinfo

import resultspoolmanager
import resultspool
import communication
import protocol
import core
import cStringIO

import google
import maaycentral

class Core:
    #
    # The name of the parameters are explicit.
    #
    def __init__(self, nodeID, nodeIP, nodePort):
        self.__nodeID = nodeID
        self.__nodeIP = nodeIP
        self.__nodePort = nodePort
        self.__counter = 0
        self.resultSpoolManager = resultspoolmanager.ResultSpoolManager()
        self.__stop_update_matching = 0

        # used to keep track of received queries to avoid cycle
        # query_id => (query, sender_node, timestamp, expected_hit_count, hit_sent, hits)

        self.__waitingProcess = 0
        self.__waitingProcessLock = threading.Lock()

        # update my node information
        nodeInfo = globalvars.database.getNodeInfo(nodeID)
        if not nodeInfo:
            nodeInfo = maay.datastructure.nodeinfo.NodeInfo(nodeID, nodeIP, nodePort, 0, 0, 0, 0, 0)
            globalvars.database.insertNodeInfo(nodeInfo)
        else:
            nodeInfo.ip = nodeIP
            nodeInfo.port = nodePort
            globalvars.database.updateNodeInfo(nodeInfo)
    
        self.__updateMatchingLock = threading.Lock()

    def suspend_low_priority_tasks(self):
        self.__waitingProcessLock.acquire()
        self.__waitingProcess += 1
        self.__waitingProcessLock.release()

    def resume_low_priority_tasks(self):
        self.__waitingProcessLock.acquire()
        self.__waitingProcess -= 1
        if self.__waitingProcess == 0:
            try:
                self.__indexationLock.release()
            except Exception, e:
                pass
        self.__waitingProcessLock.release()

    def idle(self, priority = constants.MEDIUM_PRIORITY):
#               self.__waitingProcessLock.acquire()
#               wp = self.__waitingProcess
#               self.__waitingProcessLock.release()
#               load = globalvars.systemMonitor.getProcessorLoad()
#
#               if wp > 0:
#                       if priority == constants.LOW_PRIORITY:
#                               time.sleep(load / 20)
#                       elif priority == constants.MEDIUM_PRIORITY:
#                               time.sleep(load / 40)
#               else:
#                       if priority == constants.LOW_PRIORITY:
#                               time.sleep(load / 40)
#                       elif priority == constants.MEDIUM_PRIORITY:
#                               time.sleep(load / 80)
        while globalvars.stop != 1:
            load = globalvars.systemMonitor.getProcessorLoad()
            if priority == constants.LOW_PRIORITY and load < 20:
                break
            elif priority == constants.MEDIUM_PRIORITY and load < 40:
                break
            elif priority == constants.HIGH_PRIORITY:
                break

            time.sleep(2)

#                       time.sleep(load / 10)

#               if priority == constants.LOW_PRIORITY:
#                               if 
#                       time.sleep(load / 40)
#               elif priority == constants.MEDIUM_PRIORITY:
#                       time.sleep(load / 80)

        
    def __hoeffding_deviation(self, confidence, occurence):
        return math.sqrt(-math.log(confidence / 2) / (2 * occurence))

    def compute_ranking_score(self, document_id, search_query):
        documentInfo = globalvars.database.getDocumentInfo(document_id)
        rank = 0.0
        documentScores = globalvars.database.getDocumentScores(db_document_id = documentInfo.db_document_id, words = search_query)
        for ds in documentScores:
            rank += (float(ds.relevance) + 0.0001) * (float(ds.popularity) + 0.0001) * (float(documentInfo.matching) + 0.0001)

        return rank


    # send search request to the node
    #
    def __send_search_request_to(self, query_id, TTL, ip, port, search_query, min_score, FNC, result_count):
        globalvars.communication.send_search_request_to(query_id, TTL, ip, port, search_query, min_score, FNC, result_count)

#       def recv_download_response(self, query_id, TTL, sender_nodeID, sender_nodeIP, sender_nodePort, document_id, publication_time, file_name, mime_type):
#               pass
#               globalvars.indexer.addNewDocumentToIndex(file_name, document_id, publication_time, mime_type)

#       def generateQueryID(self):
#               return self.__generateQueryID

    def __generateQueryID(self):
        while True:
            query_id = tools.maay_hash(str(time.time()))
            if not self.resultSpoolManager.getResultSpool(query_id):
                return str(query_id)

    def send_search_request(self, search_query, TTL, search_range, min_score, FNC, result_count, query_id = None):
        if not query_id:
            query_id = self.__generateQueryID()
        self.recv_search_request(query_id, TTL, self.__nodeID, self.__nodeIP, self.__nodePort, search_query, min_score, FNC, result_count, search_range)
        return query_id

    def send_download_request(self, document_id, search_query):
        globalvars.downloadManager.insertDownload(document_id, search_query)

    def recv_download_request(self, httpRequestHandler, query_id, TTL, sender_nodeID, sender_nodeIP, sender_nodePort, document_id, search_query):
        # check in the indexer if we have it
        documentInfo = globalvars.database.getDocumentInfo(document_id=document_id)
        if not documentInfo:
            print "never heard about document %s" % document_id
            # todo: forward request to a node which have a document which a close document id? 
            has_content = 0
            has_description = 0
        else:
            if documentInfo.state == maay.datastructure.documentinfo.KNOWN_STATE:
                print "I do not have the file on my disk, why do you ask me ?"
                # todo: but I can give you some other pointers
                has_content = 0
            else:
                has_content = 1
            has_description = 1

        flags = (has_content * constants.HAS_DOCUMENT_CONTENT_FLAG) | (has_description * constants.HAS_DOCUMENT_DESCRIPTION_FLAG)

        # update documentScore with the download request received and the
        # documentscore received

#               dp = documentProviders[0]
#               nodeInfo = globalvars.database.getNodeInfo(dp.node_id)

        httpRequestHandler.send_response(200)
        httpRequestHandler.end_headers()
        output = tools.file2stream(httpRequestHandler.wfile)
        protocol.sendHeader(output, constants.DOWNLOAD_RESPONSE_COMMAND, self.__generateQueryID(), constants.INIT_TTL)
        protocol.sendDownloadResponse(output, document_id, flags)
        if has_description:
            documentProviders = globalvars.database.getDocumentProviders(documentInfo.db_document_id)

            if has_content and not documentInfo.url:
                fileInfos = globalvars.database.getFileInfos(db_document_id = documentInfo.db_document_id, state = maay.datastructure.documentinfo.PUBLISHED_STATE)
                for fileInfo in fileInfos:
                    pos = fileInfo.file_name.find(globalvars.config.getValue("PublishedDocumentRoot"))
                    print "send url pos = %s" % pos
                    if pos != -1:
                        documentInfo.url = 'http://%s:%s/pub/%s' % (globalvars.ip, globalvars.port, fileInfo.file_name[pos + len(globalvars.config.getValue("PublishedDocumentRoot")) + 1:])

                        documentInfo.url = documentInfo.url.replace("\\", "/")
                        break

            protocol.sendDownloadResponseDocumentDescription(output, documentInfo.title, documentInfo.publication_time, documentInfo.mime_type, documentInfo.size, documentInfo.url or "", len(documentProviders))


            for dp in documentProviders:
                nodeInfo = globalvars.database.getNodeInfo(dp.node_id)
                protocol.sendDownloadResponseProvider(output, dp.node_id, nodeInfo.ip, nodeInfo.port, dp.last_providing_time, nodeInfo.last_seen_time, nodeInfo.bandwidth, nodeInfo.counter)

            if has_content:
                fileInfo = globalvars.database.getFileInfos(db_document_id = documentInfo.db_document_id)[0]
                protocol.sendDownloadResponseDocument(output, fileInfo.file_name, documentInfo.size)
                self.hasDownloaded(sender_nodeID, document_id, search_query, weight=DOWNLOAD_SCORE_WEIGHT)

#               c = connection.Connection(self, sender_nodeIP, sender_nodePort)
#               c.sendHeader(constants.DOWNLOAD_RESPONSE_COMMAND, query_id, TTL)
#               c.sendDownloadResponse(document_id, documentInfo.publication_time, documentInfo.mime_type, documentInfo.size, fileInfo.file_name)
#               c.close()


    def recv_search_request(self, query_id, TTL, sender_nodeID, sender_nodeIP,
            sender_nodePort, search_query, min_score, FNC, result_count, search_range):

        print "receive search request %s %s %s" % (sender_nodeID, self.__nodeID, search_range)
        # detect cycle
        if sender_nodeID != self.__nodeID and self.resultSpoolManager.getResultSpool(query_id):
            return

        # todo: change the prototype of the function to take into account
        # result_expected_count and expected_hit count

        resultSpool = globalvars.maay_core.getResultSpoolManager().getResultSpool(query_id)
        if not resultSpool:
            resultSpool = resultspool.ResultSpool(sender_nodeID, query_id, search_query, search_range, min_score, result_count, TTL, FNC, int(time.time()))
            self.resultSpoolManager.insert(resultSpool)

        search_query = resultSpool.getQuery()

        # look for unknown word in query
        # for each word, we should find a node interested into it
        # for the moment, we only replace the unknown word by the closest
        # one in levenshtein distance
#                       routing_search_query = []
#                       for word in search_query:
            # note: the closest word can be the word itself
#                               closest_word = globalvars.database.getClosestWord(word)
#                               routing_search_query.append(closest_word)

        i = 0
        # update keywords relationship
        self.manifest_interest(sender_nodeID, search_query)

        if search_range == constants.INTERNET_SEARCH_RANGE:
            results = google.search(search_query, result_count)
            for result in results:
                resultSpool.addResult(result)
            return
        elif search_range == constants.INTRANET_SEARCH_RANGE:
            results = maaycentral.search(search_query, result_count)
            for result in results:
                resultSpool.addResult(result)
            return


        # send its own responses
        documentInfos = globalvars.database.getBestDocumentInfos(search_query, min_score, result_count, search_range)

        for documentInfo in documentInfos:
            ranking_score = self.compute_ranking_score(documentInfo.document_id, search_query)
#                               print "insert document"
            # todo: find where the publication_time become a float ??
            result = resultspool.MaayResult(documentInfo.document_id, ranking_score, 0, 0, int(documentInfo.publication_time), documentInfo.state)
            resultSpool.addResult(result)

            del documentInfo

        del documentInfos

        self.flushResults()

        # forward queries to others
        if TTL < 1 or (search_range & constants.P2P_SEARCH_RANGE) == 0:
            return

        # we take random part of best node and random node
        bestNodeCount = int(math.ceil(float(FNC) / 2))
        randomNodeCount = FNC - bestNodeCount
#                       bestNodeCount = int(round(random.random() * FNC))
#                       randomNodeCount = FNC - bestNodeCount

        print "bestNodeCount = %s" % bestNodeCount
        bestNodeInfos = globalvars.database.getBestNodeInfos(search_query, bestNodeCount)
        print "randomNodeCount = %s" %   randomNodeCount
        randomNodeInfos = globalvars.database.getRandomNodeInfos(bestNodeInfos, randomNodeCount)

        adresses = []
        for nodeInfo in bestNodeInfos + randomNodeInfos:
            if nodeInfo.node_id != self.__nodeID and nodeInfo.node_id != sender_nodeID:
                adresses.append((nodeInfo.node_id, nodeInfo.ip, nodeInfo.port))
            del nodeInfo
        del bestNodeInfos
        del randomNodeInfos

        nodeTCPInfo = globalvars.potentialNodeManager.pop()
        if nodeTCPInfo: 
            adresses.append((-1, nodeTCPInfo.ip, nodeTCPInfo.port))

        for id, ip, port in adresses:
            print "id = %s, ip = %s, port = %s" % (id, ip, port)
            self.__send_search_request_to(query_id, TTL - 1, ip, port, search_query, min_score, int(math.sqrt(FNC)), result_count)

        del adresses
#               else:
#                       # take 100 random and take the best one for the distance
#                       documentInfos = globalvars.database.getRandomDocumentInfos(100)
#                       documentInfoScores = []
#                       for documentInfo in documentInfos:
#                               documentInfoScores.append((documentInfo, converter.texttools.levenshtein_distance(documentInfo.document_id, document_id)))
#                       documentInfoScores.sort(lambda x, y: x[1] - y[1])
#                       nodeInfos = []
#                       nodeInfoCount = 0
#                       for documentInfo, score in documentInfoScores:
#                               documentProviders = globalvars.database.getDocumentProviders(documentInfo.db_document_id)
#                               for documentProvider in documentProviders:
#                                       nodeInfo = globalvars.database.getNodeInfo(documentProvider.node_id)
#                                       if nodeInfo in nodeInfos:
#                                               nodeInfos.append(nodeInfo)
#                                               nodeInfoCount += 1
#                                               if nodeInfoCount >= FNC:
#                                                       break
#
#                               if nodeInfoCount >= FNC:
#                                       break
#
#
#                       for nodeInfo in nodeInfos:
#                               print "to id = %s, ip = %s, port = %s" % (nodeInfo.node_id, nodeInfo.ip, nodeInfo.port)
#                               if nodeInfo.node_id != self.__nodeID and nodeInfo.node_id != sender_nodeID:
#                                       self.__send_search_request_to(query_id, TTL - 1, nodeInfo.ip, nodeInfo.port, search_query, document_id, min_score, int(math.sqrt(FNC)), result_count - len(documentInfos))


    #
    # Update the node interest when a new message is received
    #
    def manifest_interest(self, node_id, search_query):
        if not search_query:
            return
        search_query = list(search_query)
        search_query.sort()

        claim_count_fraction = 1.0 / len(search_query)

        i = 0 

        nodeInfo = globalvars.database.getNodeInfo(node_id)

        for word in search_query:
            # skip url query
            if word.find("url:") == 0:
                continue
            wordInfo = globalvars.database.getWordInfo(word)
            if wordInfo:
                wordInfo.claim_count += claim_count_fraction
                globalvars.database.updateWordInfo(wordInfo)
            else:
                wordInfo = maay.datastructure.wordinfo.WordInfo(word, claim_count_fraction, claim_count_fraction)
                globalvars.database.insertWordInfo(wordInfo)

            nodeInfo.claim_count += claim_count_fraction
            globalvars.database.updateNodeInfo(nodeInfo)

            nodeInterest = globalvars.database.getNodeInterest(node_id, word)
            if nodeInterest == None:
                nodeInterest = maay.datastructure.nodeinterest.NodeInterest(node_id, word, claim_count_fraction, 0, 0)
                globalvars.database.insertNodeInterest(nodeInterest)
            else:
                nodeInterest.claim_count += claim_count_fraction
                globalvars.database.updateNodeInterest(nodeInterest)

            nodeInterests = globalvars.database.getNodeInterests(words = [word])
            for ni in nodeInterests:
                ni.popularity = float(ni.claim_count) /  float(wordInfo.claim_count)
                globalvars.database.updateNodeInterest(ni)

            i += 1

        nodeInterests = globalvars.database.getNodeInterests(node_id=node_id)
        for ni in nodeInterests:
            ni.specialisation = ni.claim_count / nodeInfo.claim_count
            globalvars.database.updateNodeInterest(ni)


    def getNodeID(self):
        return self.__nodeID

    def getNodeIP(self):
        return self.__nodeIP

    def getNodePort(self):
        return self.__nodePort
        
    def cleanTemporaryDirectory(self):
        print "Cleaning Directory"
        # check if the cleaning directory is ok ? "suppose someone set it to C:\"...
        #TODO: check if the temporary directory is ok?

    def hasDownloaded(self, node_id, document_id, search_query, weight = 1.0):
        # increase its counters
        documentInfo = globalvars.database.getDocumentInfos(document_id=document_id)[0]
        documentInfo.download_count += weight
        globalvars.database.updateDocumentInfo(documentInfo)
        
        print "has downloaded = %s" % search_query

        if search_query == None:
            return

        # update word statistics
        # increase interest of sender for the download words
        search_query = list(search_query)

        search_query.sort()
        i = 0

        self.manifest_interest(node_id, search_query)

        for keyword1 in search_query:
            if keyword1.find("url:") == 0:
                continue

            documentScore = globalvars.database.getDocumentScore(documentInfo.db_document_id, keyword1)
            if not documentScore:
                documentScore = maay.datastructure.documentscore.DocumentScore(documentInfo.db_document_id, keyword1, -1, float(weight) / len(search_query), 0.0, 0.0)
                globalvars.database.insertDocumentScore(documentScore)
        
            documentScore.download_count += float(weight) / len(search_query)
            wordInfo = globalvars.database.getWordInfo(keyword1)
            wordInfo.download_count += float(weight) / len(search_query)

            globalvars.database.updateWordInfo(wordInfo)
            globalvars.database.updateDocumentScore(documentScore)

            documentScores = globalvars.database.getDocumentScores(db_document_id = documentInfo.db_document_id)
            for ds in documentScores:
                if ds.download_count == 0:
                    continue
                ds.popularity = max(0, float(ds.download_count) / wordInfo.download_count - self.__hoeffding_deviation(constants.hoeffding_confidence, wordInfo.download_count))
                ds.relevance = max(0, float(ds.download_count) / documentInfo.download_count - self.__hoeffding_deviation(constants.hoeffding_confidence, documentInfo.download_count))
                globalvars.database.updateDocumentScore(ds)
                if ds.popularity > 0:
                    print "update rel = %s" % ds.popularity


            del documentScores
            
            continue

            documentScores = globalvars.database.getDocumentScores(words = (keyword1,))
            for ds in documentScores:
                d = globalvars.database.getDocumentInfo(db_document_id = ds.db_document_id)
                if not d:
                    globalvars.database.deleteDocumentScores(db_document_id=ds.db_document_id)
                    continue
                if d.state == maay.datastructure.documentinfo.KNOWN_STATE:
                    continue
                if d.download_count <= 1:
                    continue
                if ds.download_count == 0:
                    continue
                ds.popularity = max(0, float(ds.download_count) / wordInfo.download_count - self.__hoeffding_deviation(constants.hoeffding_confidence, wordInfo.download_count))
                ds.relevance = max(0, float(ds.download_count) / d.download_count - self.__hoeffding_deviation(constants.hoeffding_confidence, d.download_count))
                globalvars.database.updateDocumentScore(ds)

            del documentScores
            del wordInfo
            del documentScore

        self.updateDocumentMatching(document_id=document_id)
        del documentInfo

    def getBandwidth(self):
        return 10

    def getCounter(self):
        return 0

    def updateNodeInfo(self, node_id, ip, port, bandwidth, counter, last_seen_time):
        nodeInfo = globalvars.database.getNodeInfo(node_id)
        if nodeInfo:
            if nodeInfo.last_seen_time > last_seen_time:
                return nodeInfo
            nodeInfo.ip = ip
            nodeInfo.port = port
            nodeInfo.bandwidth = bandwidth
            nodeInfo.counter = counter
            nodeInfo.last_seen_time = last_seen_time
            globalvars.database.updateNodeInfo(nodeInfo)
        else:
            nodeInfo = maay.datastructure.nodeinfo.NodeInfo(node_id, ip, port, counter, last_seen_time, 0, 0, bandwidth)
            globalvars.database.insertNodeInfo(nodeInfo)

        return nodeInfo

    def updateDocumentInfo(self, document_id, mime_type, title, size, publication_time, url, state = maay.datastructure.documentinfo.KNOWN_STATE):
        documentInfo = globalvars.database.getDocumentInfo(document_id=document_id)
        if not documentInfo:
            documentInfo = maay.datastructure.documentinfo.DocumentInfo(None, document_id, mime_type,
                    title, size, "", publication_time, state, 0, url, 0, 0)
            globalvars.database.insertDocumentInfo(documentInfo)
        elif not documentInfo.state in (maay.datastructure.documentinfo.PUBLISHED_STATE, maay.datastructure.documentinfo.PRIVATE_STATE, maay.datastructure.documentinfo.CACHED_STATE):
            documentInfo.title = title
            documentInfo.mime_type = mime_type
            if documentInfo.state != maay.datastructure.documentinfo.PRIVATE_STATE:
                documentInfo.state = state
            documentInfo.size = size
            documentInfo.publication_time = publication_time
    
            if not documentInfo.url:
                documentInfo.url = url
            globalvars.database.updateDocumentInfo(documentInfo)
        else:
            if not documentInfo.url:
                documentInfo.url = url
                globalvars.database.updateDocumentInfo(documentInfo)

        return documentInfo

    def processDocumentScore(self, db_document_id, word, relevance, popularity, excerpt, excerpt_position, word_position, nodeInfo):
        documentInfo = globalvars.database.getDocumentInfos(db_document_id = db_document_id, get_text=1)[0]

        documentScore = globalvars.database.getDocumentScore(db_document_id, word)

        if documentInfo.state in (maay.datastructure.documentinfo.PUBLISHED_STATE, maay.datastructure.documentinfo.CACHED_STATE, maay.datastructure.documentinfo.PRIVATE_STATE):
            print "published doc score"
            return documentScore
    
        if not documentScore:
            documentScore = maay.datastructure.documentscore.DocumentScore(documentInfo.db_document_id, word, word_position, 0, relevance, popularity)
            if not documentInfo.text:
                buffer = cStringIO.StringIO()
                for i in xrange(excerpt_position):
                    buffer.write(' ')
                buffer.write(excerpt)
                documentInfo.text = buffer.getvalue()
            else:
                buffer = cStringIO.StringIO()
                buffer.write(documentInfo.text[:excerpt_position])
                for i in xrange(excerpt_position - len(documentInfo.text[:excerpt_position])):
                    buffer.write(' ')
                buffer.write(excerpt)
                buffer.write(documentInfo.text[excerpt_position + len(excerpt):])
                documentInfo.text = buffer.getvalue()

            globalvars.database.updateDocumentInfo(documentInfo)

            globalvars.database.insertDocumentScore(documentScore)
        else:
            # todo: if we have already something, change it according to
            # some criteria
            documentScore.relevance = relevance
            documentScore.popularity = popularity
            globalvars.database.updateDocumentScore(documentScore)

        return documentScore

    def updateDocumentProvider(self, db_document_id, node_id, last_providing_time):
        print "update document provider %s %s" % (db_document_id,node_id)
        documentProvider = globalvars.database.getDocumentProvider(db_document_id, node_id)
        if documentProvider:
            if last_providing_time > documentProvider.last_providing_time:
                documentProvider.last_seen_time = last_providing_time
                globalvars.database.updateDocumentProvider(documentProvider)
        else:
            documentProvider = maay.datastructure.documentprovider.DocumentProvider(db_document_id, node_id, last_providing_time)
            globalvars.database.insertDocumentProvider(documentProvider)

    def getResultSpoolManager(self):
        return self.resultSpoolManager

    # function periodically called (each 1 sec) to send back response to
    # search requester in order not to always send message request (bufferize)
    def flushResults(self):
        t = int(time.time())
        for rs in self.resultSpoolManager.getResultSpools():

            if rs.getNodeID() == self.__nodeID:
                continue

            if t - rs.getQueryTime() > constants.result_spool_lifetime:
                self.resultSpoolManager.removeResultSpool(rs)
                continue

            if rs.getSentResultCount() >= rs.getExpectedResultCount():
                continue

            # keep this resultspool

            documentIDs = rs.getBestUnsentResults()
            if len(documentIDs) == 0:
                continue

            nodeInfo = globalvars.database.getNodeInfo(rs.getNodeID())
            print "flush results to %s" % rs.getNodeID()
                # todo : if the connection is local, make a shortcut
#                               c = protocol.Protocol(self, nodeInfo.ip, nodeInfo.port)
            connection = httplib.HTTPConnection(nodeInfo.ip, nodeInfo.port)
            connection.putrequest("POST", "/message")
            connection.endheaders()

            protocol.sendHeader(connection, constants.SEARCH_RESPONSE_COMMAND, rs.getQueryID(), 0)
            protocol.sendSearchResponseInfo(connection, len(documentIDs))

            for document_id in documentIDs:
                documentInfo = globalvars.database.getDocumentInfos(document_id = document_id, get_text = 1)[0]
                if not documentInfo.url:
                    fileInfos = globalvars.database.getFileInfos(db_document_id = documentInfo.db_document_id, state = maay.datastructure.documentinfo.PUBLISHED_STATE)
                    for fileInfo in fileInfos:
                        pos = fileInfo.file_name.find(globalvars.config.getValue("PublishedDocumentRoot"))
                        if pos != -1:
                            documentInfo.url = 'http://%s:%s/pub/%s' % (globalvars.ip, globalvars.port, fileInfo.file_name[pos + len(globalvars.config.getValue("PublishedDocumentRoot")) + 1:])

                            documentInfo.url = documentInfo.url.replace("\\", "/")
                            break

            
                queryDocumentScores = globalvars.database.getDocumentScores(documentInfo.db_document_id, rs.getQuery())
                relevantDocumentScores = globalvars.database.getBestRelevantDocumentScores(documentInfo.db_document_id, constants.relevant_document_score_count + len(rs.getQuery()))
                documentProviders = globalvars.database.getDocumentProviders(documentInfo.db_document_id)

                documentScores = queryDocumentScores[:]

                for ds in relevantDocumentScores:
                    add = 1
                    for word in rs.getQuery():
                        if ds.word == word:
                            add = 0
                            break
                    if add:
                        documentScores.append(ds)

                url = documentInfo.url
                if not url:
                    url = ""
#                               if url:
#                                       if url.find('/') == 0:
#                                               url = "http://%s:%s%s/pub" % (globalvars.hostname, globalvars.port, url)
#                               else:
#                                       url = ""

                protocol.sendSearchResponseHitInfo(connection, document_id, documentInfo.mime_type, url, documentInfo.publication_time, documentInfo.size, documentInfo.title, len(documentScores), len(documentProviders))

                for ds in documentScores:
                    pos = ds.position
                    text = documentInfo.text
                    if pos >= constants.MAX_TEXT_CONTENT_STORED_SIZE:
                        pos = 0
                    start = max(0, pos - constants.EXCERPT_HALF_SIZE)
                    if start > 0:
                        while start < pos and text[start] != ' ':
                            start += 1
                        start += 1

                    end = min(len(text) - 1, start + constants.EXCERPT_SIZE)

                    if end < len(text) - 1:
                        while end > pos and text[end] != ' ':
                            end -= 1

                    excerpt = documentInfo.text[start:end]
                    print "excerpt = %s (%s,%s)" % (excerpt, start, end)

                    protocol.sendSearchResponseHitScore(connection, ds.word, ds.relevance, ds.popularity, excerpt, start, ds.position)

                for dp in documentProviders:
                    ni = globalvars.database.getNodeInfo(dp.node_id)
                    if ni.node_id == self.__nodeID:
                        ni.last_seen_time == int(time.time())
                    protocol.sendSearchResponseHitProvider(connection, dp.node_id, ni.ip, ni.port, dp.last_providing_time, ni.last_seen_time, ni.bandwidth, ni.counter)

            connection.close()

    def updateAffinity(self):
        print "task: update affinity"
        nodeInterestsHT1 = globalvars.database.getNodeInterestsHT(self.__nodeID)
        nodeInfos = globalvars.database.getNodeInfos()
        for nodeInfo in nodeInfos:
            affinity = 0.0

            nodeInterestsHT2 = globalvars.database.getNodeInterestsHT(nodeInfo.node_id)
            if len(nodeInterestsHT1) < len(nodeInterestsHT2):
                for nodeInterest in nodeInterestsHT1.values():
                    if nodeInterestsHT2.has_key(nodeInterest.word):
                        affinity += nodeInterestsHT1[nodeInterest.word].specialisation * nodeInterestsHT2[nodeInterest.word].expertise
            else:
                for nodeInterest in nodeInterestsHT2.values():
                    if nodeInterestsHT1.has_key(nodeInterest.word):
                        affinity += nodeInterestsHT1[nodeInterest.word].specialisation * nodeInterestsHT2[nodeInterest.word].expertise

            nodeInfo.affinity = affinity 
            globalvars.database.updateNodeInfo(nodeInfo)

            del nodeInfo
            del nodeInterestsHT2
    
        del nodeInterestsHT1
        del nodeInfos

    def executeAging(self):
        print "execute aging"
        claim_count, download_count = globalvars.database.getWordSum()
        print "claim = %s, download = %s" % (claim_count, download_count)
        if claim_count > 1000:
            globalvars.database.executeClaimAging()
        if download_count > 1000:
            globalvars.database.executeDownloadAging()              

    def updateDocumentMatching(self, db_document_id=None, document_id=None):
        nodeInterestsHT = globalvars.database.getNodeInterestsHT(self.__nodeID)

        documentInfo = globalvars.database.getDocumentInfo(db_document_id = db_document_id, document_id = document_id, get_text=0)
        if not documentInfo:
            return

        matching = 0.0
        documentScoresHT = globalvars.database.getDocumentScoresHT(documentInfo.db_document_id)

        if len(documentScoresHT) < len(nodeInterestsHT):
            for documentScore in documentScoresHT.values():
                nodeInterest = nodeInterestsHT.get(documentScore.word)
                if nodeInterest:
                    matching += (nodeInterest.specialisation + 0.01) * (documentScore.relevance + 0.01)
        else:
            for nodeInterest in nodeInterestsHT.values():
                documentScore = documentScoresHT.get(nodeInterest.word)
                if documentScore:
                    matching += (nodeInterest.specialisation + 0.01) * (documentScore.relevance + 0.01)

        documentInfo.matching = matching 
        globalvars.database.updateDocumentInfo(documentInfo)

    def updateMatching(self):
        self.__updateMatchingLock.acquire()
        if self.__stop_update_matching == 1:
            return



        nodeInterestsHT = globalvars.database.getNodeInterestsHT(self.__nodeID)

        max_db_document_id = globalvars.database.getDocumentMaxDBDocumentID()

        documentInfo = globalvars.database.getDocumentInfo(db_document_id = 1)

        for i in xrange(max_db_document_id):
            documentInfo = globalvars.database.getDocumentInfo(db_document_id = i, get_text=0)
            if not documentInfo:
                continue
            globalvars.maay_core.idle(priority=constants.LOW_PRIORITY)
            if self.__stop_update_matching == 1:
                break

            matching = 0.0

            documentScoresHT = globalvars.database.getDocumentScoresHT(documentInfo.db_document_id)

            if len(documentScoresHT) < len(nodeInterestsHT):
                for documentScore in documentScoresHT.values():
                    if nodeInterestsHT.has_key(documentScore.word):
                        matching += (nodeInterestsHT[documentScore.word].specialisation + 0.01) * (documentScore.relevance + 0.01)
            else:
                for nodeInterest in nodeInterestsHT.values():
                    if documentScoresHT.has_key(nodeInterest.word):
                        matching += (nodeInterest.specialisation + 0.01) * (documentScoresHT[nodeInterest.word].relevance + 0.01)

            documentInfo.matching = matching 
            globalvars.database.updateDocumentInfo(documentInfo)

            del documentInfo
            for key, val in documentScoresHT.items():
                del documentScoresHT[key]
                del val
            del documentScoresHT
            

        for key, val in nodeInterestsHT.items():
            del nodeInterestsHT[key]
            del val
        del nodeInterestsHT

        try:
            self.__updateMatchingLock.release()
        except:
            pass


    def stopUpdateMatching(self):
        self.__stop_update_matching = 1

        self.__updateMatchingLock.acquire()

        try:
            self.__updateMatchingLock.release()
        except:
            pass
                    
