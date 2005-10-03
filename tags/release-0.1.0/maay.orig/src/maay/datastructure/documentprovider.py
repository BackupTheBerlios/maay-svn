"""
  DocumentProvider
"""

class DocumentProvider:
    def __init__(self, db_document_id, node_id, last_providing_time):
        self.node_id = node_id
        self.db_document_id = db_document_id
        self.last_providing_time = last_providing_time

    def __str__(self):
        return "DocumentProvider: db_document_id=%s, node_id=%s, last_providing_time=%s" % (self.node_id, self.db_document_id, self.last_providing_time)
