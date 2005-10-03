import httplib
import serializer
import binascii

import constants
import globalvars

# faire un readHTTPHeader

def readHeader(input):
    return (
            # protocol version
            serializer.read_string(input, 4),
            # vendor
            serializer.read_string(input, 16),
            # node ID
#               serializer.read_string(input, 20),
            binascii.b2a_hex(serializer.read_string(input, 20)),
            # node IP
            serializer.read_ip(input),
            # node Port
            serializer.read_short(input),
            # node bandwidth
            serializer.read_integer(input),
            # node counter
            serializer.read_integer(input),
            # command type
            serializer.read_char(input),
            # query ID
            binascii.b2a_hex(serializer.read_string(input, 20)),
            # TTL
            serializer.read_char(input)
    )


def readSearchRequest(input):
    # min_score
    min_score = serializer.read_float(input)
    # forwarding node count
    forwarding_node_count = serializer.read_char(input)
    # result count
    result_count = serializer.read_char(input)
    # search query word count 
    word_count = serializer.read_char(input)
    search_query = []
    for i in range(0, word_count):
        search_query.append(serializer.read_vstring(input))
    return (min_score, forwarding_node_count, result_count, search_query)

def readSearchResponseInfo(input):
    return (
            # hit count
            serializer.read_char(input)
    )

def readSearchResponseHitInfo(input):
    return (
            # document id
            binascii.b2a_hex(serializer.read_string(input, 20)),
            # mime_type
            serializer.read_vstring(input),
            # url
            serializer.read_vstring(input),
            # publication time
            serializer.read_integer(input),
            # file size
            serializer.read_integer(input),
            # title
            serializer.read_vstring(input),
            # score count
            serializer.read_char(input),
            # provider count
            serializer.read_char(input)
    )

def readSearchResponseHitScore(input):
    return (
            # word
            serializer.read_vstring(input),
            # relevance
            serializer.read_float(input),
            # popularity
            serializer.read_float(input),
            # excerpt
            serializer.read_vstring(input),
            # excerpt position
            serializer.read_integer(input),
            # position
            serializer.read_integer(input)
    )

def readSearchResponseHitProvider(input):
    return (
            # node id
#               serializer.read_string(input, 20),
            binascii.b2a_hex(serializer.read_string(input, 20)),
            # node ip
            serializer.read_ip(input),
            # node port
            serializer.read_short(input),
            # last storing time
            serializer.read_integer(input),
            # last seen time
            serializer.read_integer(input),
            # bandwidth
            serializer.read_integer(input),
            # counter
            serializer.read_integer(input)
    )

def readDownloadRequest(input):
    document_id = binascii.b2a_hex(serializer.read_string(input, 20))
    word_count = serializer.read_char(input)
    search_query = [];
    for i in range(0, word_count):
        search_query.append(serializer.read_vstring(input))
    return (document_id, search_query)

def readDownloadResponse(input):
    # document id
    document_id = binascii.b2a_hex(serializer.read_string(input, 20))
    flags = serializer.read_short(input)
    # content
#       content = serializer.read_string(input, size)
    return (document_id, flags)

def readDownloadResponseDocumentDescription(input):
    title = serializer.read_vstring(input)
    publication_time = serializer.read_integer(input)
    mime_type = serializer.read_vstring(input)
    size = serializer.read_integer(input)
    url = serializer.read_vstring(input)
    provider_count = serializer.read_short(input)
    return (title, publication_time, mime_type, size, url, provider_count)

def readDownloadResponseHitProvider(input):
    return (
            # node id
#               serializer.read_string(input, 20),
            binascii.b2a_hex(serializer.read_string(input, 20)),
            # node ip
            serializer.read_ip(input),
            # node port
            serializer.read_short(input),
            # last storing time
            serializer.read_integer(input),
            # last seen time
            serializer.read_integer(input),
            # bandwidth
            serializer.read_integer(input),
            # counter
            serializer.read_integer(input)
    )

def readDownloadResponseInput(input):
    return input
