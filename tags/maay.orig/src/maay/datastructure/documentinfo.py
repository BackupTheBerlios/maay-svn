"""
  DocumentInfo
"""

PUBLISHED_STATE = 1 << 0 # 1
CACHED_STATE = 1 << 1 # 2
KNOWN_STATE = 1 << 2 # 4
PRIVATE_STATE = 1 << 3 # 8
UNKNOWN_STATE = 1 << 9 # 

__state_strings = {PUBLISHED_STATE: 'published',
                   CACHED_STATE: 'cached',
                   KNOWN_STATE: 'known',
                   PRIVATE_STATE: 'private',
                   UNKNOWN_STATE: 'unknown'
                  }

def state_str(state):
    print "state_str = %s" % state
    return __state_strings[state]

class DocumentInfo:
    def __init__(self, db_document_id, document_id, mime_type, title, size, text, publication_time, state, download_count, url, matching, indexed):
        self.db_document_id = db_document_id
        self.document_id = document_id
        self.mime_type = mime_type
        self.title = title
        self.size = size
        self.text = text
        self.state = state
        self.download_count = download_count
        self.publication_time = publication_time
        self.url = url
        self.matching = matching
        self.indexed = indexed

    def __str__(self):
        return "DocumentInfo: db_document_id=%s, document_id=%s, mime_type=%s, title=%s, size=%s, state=%s, download_count=%s, publication_time=%s, url=%s, matching=%s, checked=%s, text=%s" % (self.db_document_id, self.document_id, self.mime_type, self.title, self.size, self.state, self.download_count, self.publication_time, self.url, self.matching, self.checked, self.text)
