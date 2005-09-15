class DocumentScore:

    def __init__(self, db_document_id, word, position, download_count, relevance, popularity):
        self.db_document_id = db_document_id
        self.word = word
        self.position = position
        self.download_count = download_count
        self.relevance = relevance
        self.popularity = popularity

