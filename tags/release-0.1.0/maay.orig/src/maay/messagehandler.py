# This modules handles messages incoming.

import constants
import time

import core
import response
import globalvars
import maay.datastructure.documentinfo
import tools
import protocol
import resultspool

def handleMessage(httpRequestHandler):
    # read message content
    (protocol_version, vendor, node_id, ip, port, bandwidth, counter, command_type, queryID, TTL) =  response.readHeader(httpRequestHandler.rfile)

    last_seen_time = int(time.time())

    nodeInfo = globalvars.maay_core.updateNodeInfo(node_id, ip, port, bandwidth, counter, last_seen_time)

    # update information on the node
    # we have to forward them back also, and bufferize them before
    # forwarding them back
    # check error before

    if command_type == constants.SEARCH_REQUEST_COMMAND:
        (min_score, forwarding_node_count, result_count, search_query) =  response.readSearchRequest(httpRequestHandler.rfile)
        globalvars.maay_core.recv_search_request(queryID, TTL, node_id, ip, port, search_query, min_score, forwarding_node_count, result_count, constants.MAAY_SEARCH_RANGE)

        globalvars.maay_core.manifest_interest(node_id, search_query)

    elif command_type == constants.SEARCH_RESPONSE_COMMAND:
            
        # if I receive answers of a unknown query, do nothing
        resultSpool = globalvars.maay_core.getResultSpoolManager().getResultSpool(queryID)
        if not resultSpool:
            return

        search_query = resultSpool.getQuery()

        globalvars.maay_core.manifest_interest(node_id, search_query)
        hit_count = response.readSearchResponseInfo(httpRequestHandler.rfile)
        for i in range(0, hit_count):
            (document_id, mime_type, url, publication_time, file_size, title, score_count, provider_count) = response.readSearchResponseHitInfo(httpRequestHandler.rfile)

            # update information on the document
#                       print (document_id, mime_type, url, publication_time, file_size, title, score_count, provider_count) 
            documentInfo = globalvars.maay_core.updateDocumentInfo(document_id, mime_type, title, file_size, publication_time, url)

            # todo 0 should be the score/rank of the document
#                       rank = 0.0
                        
            for j in range(0, score_count):
                (word, relevance, popularity, excerpt, excerpt_position, word_position) = response.readSearchResponseHitScore(httpRequestHandler.rfile)
#                               print (word, relevance, popularity, excerpt) 
                # update information on the word in the document
                print "process document scores"
                ds = globalvars.maay_core.processDocumentScore(documentInfo.db_document_id, word, relevance, popularity, excerpt, excerpt_position, word_position, nodeInfo)

#                               if word in search_query:
#                                       rank += (float(ds.relevance) + 0.0001) * (float(ds.popularity) + 0.0001)

            ranking_score = globalvars.maay_core.compute_ranking_score(document_id, search_query)
            globalvars.maay_core.updateDocumentMatching(document_id=document_id)

            result = resultspool.MaayResult(document_id, ranking_score, 0, 0, int(publication_time), documentInfo.state)
            resultSpool.addResult(result)

            for j in xrange(provider_count):
                (node_id, ip, port, last_storing_time, last_seen_time, bandwidth, counter) = response.readSearchResponseHitProvider(httpRequestHandler.rfile)

                globalvars.maay_core.updateNodeInfo(node_id, ip, port, bandwidth, counter, last_seen_time)
                globalvars.maay_core.manifest_interest(node_id, search_query)

                # update information on the document provider (node)
                globalvars.maay_core.updateDocumentProvider(documentInfo.db_document_id, node_id, last_storing_time)
    elif command_type == constants.DOWNLOAD_REQUEST_COMMAND:
        (document_id, search_query) = response.readDownloadRequest(httpRequestHandler.rfile)
        globalvars.maay_core.manifest_interest(node_id, search_query)
        globalvars.maay_core.recv_download_request(httpRequestHandler, queryID, TTL, node_id, ip, port, document_id, search_query)

    if command_type != constants.DOWNLOAD_REQUEST_COMMAND:
        httpRequestHandler.send_response(200)
        httpRequestHandler.end_headers()
        protocol.sendHeader(tools.file2stream(httpRequestHandler.wfile), constants.PONG_COMMAND, queryID, 0)


