import serializer
import constants
import binascii

import globalvars

def sendHeader(output, command_type, queryID, TTL):
    serializer.send_string(output, constants.PROTOCOL_VERSION, 4)
    serializer.send_string(output, constants.VENDOR, 16)
    serializer.send_string(output, binascii.a2b_hex(globalvars.maay_core.getNodeID()), 20)
    serializer.send_ip(output, globalvars.maay_core.getNodeIP())
    serializer.send_short(output, globalvars.maay_core.getNodePort())
    serializer.send_integer(output, globalvars.maay_core.getBandwidth())
    serializer.send_integer(output, globalvars.maay_core.getCounter())
    serializer.send_char(output, command_type)
    serializer.send_string(output, binascii.a2b_hex(queryID), 20)
    serializer.send_char(output, TTL)

def sendSearchRequest(output, min_score, forwarding_node_count, result_count, search_query):
    serializer.send_float(output, min_score)
    serializer.send_char(output, forwarding_node_count)
    print "result_count = %s" % result_count
    serializer.send_char(output, result_count)
    serializer.send_char(output, len(search_query))
    for word in search_query:       
        serializer.send_vstring(output, word)           

def sendSearchResponseInfo(output, hit_count):
    serializer.send_char(output, hit_count)

def sendSearchResponseHitInfo(output, document_id, mime_type, url, publication_time, file_size, title, score_count, provider_count):
    serializer.send_string(output, binascii.a2b_hex(document_id), 20)
    serializer.send_vstring(output, mime_type)
    serializer.send_vstring(output, url)
    serializer.send_integer(output, publication_time)
    serializer.send_integer(output, file_size)
    serializer.send_vstring(output, title)
    serializer.send_char(output, score_count)
    serializer.send_char(output, provider_count)

def sendSearchResponseHitScore(output, word, relevance, popularity, excerpt, excerpt_position, word_position):
    serializer.send_vstring(output, word)
    serializer.send_float(output, relevance)
    serializer.send_float(output, popularity)
    serializer.send_vstring(output, excerpt)
    serializer.send_integer(output, excerpt_position)
    serializer.send_integer(output, word_position)

def sendSearchResponseHitProvider(output, node_id, node_ip, node_port, last_storing_time, last_seen_time, bandwidth, counter):
    serializer.send_string(output, binascii.a2b_hex(node_id), 20)
    serializer.send_ip(output, node_ip)
    serializer.send_short(output, node_port)
    serializer.send_integer(output, last_storing_time)
    serializer.send_integer(output, last_seen_time)
    serializer.send_integer(output, bandwidth)
    serializer.send_integer(output, counter)

#def close():
#       output.close()

# view after for multi-source
def sendDownloadRequest(output, document_id, search_query):
    serializer.send_string(output, binascii.a2b_hex(document_id), 20)
    serializer.send_char(output, len(search_query))
    for word in search_query:
        serializer.send_vstring(output, word)

def sendDownloadResponse(output, document_id, flags):
    serializer.send_string(output, binascii.a2b_hex(document_id), 20)
    serializer.send_short(output, flags)

def sendDownloadResponseDocumentDescription(output, title, publication_time, mime_type, size, url, provider_count):
    serializer.send_vstring(output, title)
    serializer.send_integer(output, publication_time)
    serializer.send_vstring(output, mime_type)
    serializer.send_integer(output, size)
    serializer.send_vstring(output, url)
    serializer.send_short(output, provider_count)

def sendDownloadResponseLink(output, path, link_time, document_id):
    None

def sendDownloadResponseProvider(output, node_id, node_ip, node_port, last_storing_time, last_seen_time, bandwidth, counter):
    serializer.send_string(output, binascii.a2b_hex(node_id), 20)
    serializer.send_ip(output, node_ip)
    serializer.send_short(output, node_port)
    serializer.send_integer(output, last_storing_time)
    serializer.send_integer(output, last_seen_time)
    serializer.send_integer(output, bandwidth)
    serializer.send_integer(output, counter)


def sendDownloadResponseDocument(output, file_name, size):
    fd = file(file_name, 'rb')
    l = 0
    while l < size:
        buf = fd.read(8192)
        output.send(buf)
        l += len(buf)

