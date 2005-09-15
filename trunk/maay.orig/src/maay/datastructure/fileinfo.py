REMOVED_FILE_STATE = 0
CREATED_FILE_STATE = 1
MODIFIED_FILE_STATE = 2
UNMODIFIED_FILE_STATE = 3
NOT_INDEXED_FILE_STATE = 4

class FileInfo:
    def __init__(self, file_name, file_time, db_document_id, state, file_state):
        self.file_name = file_name
        self.file_time = file_time
        self.db_document_id = db_document_id
        self.state = state
        self.file_state = file_state

    def __str__(self):
        return "FileInfo: file_name=%s, file_time=%s, db_document_id=%s, state=%s, file_state=%s" % (self.file_name, self.file_time, self.db_document_id, self.state, self.file_state)
