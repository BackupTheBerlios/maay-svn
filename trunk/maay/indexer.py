"""This module contains the indexer code.
The indexer crawl files on disk, analyse the textual content
of a file and update the indexes.

TODO: analyse the God class into something understandable
"""

__revision__ = '$Id$'

import os, stat
import sha
from xmlrpclib import ServerProxy
import mimetypes

from maay import converter
from maay.configuration import Configuration
from maay.dbentity import Document, FileInfo

class AuthenticationError(Exception):
    """raised when authentication on xmlrpc server failed"""

def makeDocumentId(filename):
    """return the SHA hash value from of the contents of the file"""
    stream = file(filename, 'rb')
    hasher = sha.sha()
    data = stream.read(4096)
    while data:        
        hasher.update(data)
        data = stream.read(4096)
    stream.close()
    return hasher.hexdigest()
    
# TODO: manage published/private documents
# TODO: manage periodical runs
# TODO: memorize state of indexed document to avoid db lookup at each run
# TODO: do an initial db query to initialize the indexation state (?)
class Indexer:
    """An Indexer instance periodically looks in the configured
    directories for files to index If it detects changes in known
    files, it sends a request to the Querier (via xmlrpc) to index the
    file, giving the Querier information on the file. The querier may
    decide to do nothing if it detects that the database is up-to-date.
    """
    
    def __init__(self, indexerConfig):
        self.indexerConfig = indexerConfig
        username = self.indexerConfig.user
        password = self.indexerConfig.password
        host = self.indexerConfig.host
        port = self.indexerConfig.port
        self.serverProxy = ServerProxy('http://%s:%s' % (host, port), allow_none=True)
        self.cnxId = self.serverProxy.authenticate(username, password)
        if not self.cnxId:
            raise AuthenticationError("Failed to connect as '%s'" % username)
        
    def getFileIterator(self):
        indexed = self.indexerConfig.index_dir
        skipped = self.indexerConfig.skip_dir
        return FileIterator(indexed, skipped)

    def start(self):
        for filename in self.getFileIterator():
            lastModificationTime = os.path.getmtime(filename)
            lastIndexationTime = self.getLastIndexationTime(filename)
            if lastIndexationTime > lastModificationTime:
                print "%s didn't change since last indexation"
            else:
                fileSize = os.path.getsize(filename)
                try:
                    title, text, links, offset = converter.extractWordsFromFile(filename)
                except converter.IndexationFailure, exc:
                    print exc
                    continue
                docId = makeDocumentId(filename)
                mime_type = mimetypes.guess_type(filename)[0]
                mime_type = mimetypes.guess_type(filename)

                self.indexDocument(filename, title, text, fileSize, lastModificationTime,
                                   docId, mime_type, Document.PUBLISHED_STATE)
        # FIXME: do some cleanup of the database after indexing
        # * remove FileInfo for files that are no longer on disk
        # * remove Documents with no corresponding files
        
    def getLastIndexationTime(self, filename):
        lastIndexationTime = self.serverProxy.lastIndexationTime(self.cnxId, filename)
        if lastIndexationTime is None:
            raise AuthenticationError("Bad cnxId sent to the server")
        return lastIndexationTime

    def indexDocument(self, filename, title, text, fileSize,
                      lastModTime, content_hash, mime_type, state,
                      file_state=FileInfo.CREATED_FILE_STATE):
        print "I should now update DB with all these new words ! (%s)" % filename
        self.serverProxy.indexDocument(self.cnxId, filename, title, text,
                                       fileSize, lastModTime, content_hash,
                                       mime_type, state, file_state)
        
    
     
class FileIterator:
    """provide a simple way to walk through indexed dirs"""
    def __init__(self, indexed, skipped=None):
        self.indexed = indexed
        self.skipped = skipped or []
        for dirpath in self.indexed:
            assert os.path.isabs(dirpath), "relative paths not supported !"
        for dirpath in self.skipped:
            assert os.path.isabs(dirpath), "relative paths not supported !"

    def __iter__(self):
        for path in self.indexed:
            # test path not in self.skipped (dummy config files)
            if path not in self.skipped:
                for dirpath, dirnames, filenames in os.walk(path):
                    self._removeSkippedDirnames(dirpath, dirnames)
                    for filename in filenames:
                        yield os.path.join(dirpath, filename)
                    
    def _removeSkippedDirnames(self, dirpath, dirnames):
        """removed skipped directories from dirnames (inplace !)"""
        for dirname in dirnames[:]:
            abspath = os.path.join(dirpath, dirname)
            if abspath in self.skipped:
                dirnames.remove(dirname)



## main() ##################################################

class IndexerConfiguration(Configuration):
    options = [
        ('host',
         {'type' : "string", 'metavar' : "<host>", 'short' : "H",
          'help' : "where Maay node can be found",
          'default' : "localhost",
          }),

        ('port',
         {'type' : "int", 'metavar' : "<int>", 'short' : "P",
          'help' : "which port to use",
          'default' : 6789,
        }),

        ('user',
         {'type': 'string',
          'metavar': '<userid>', 'short': 'u',
          'help': 'identifier to use to connect to the database',
          'default' : "maay",
          }),

        ('password',
         {'type': 'string',
          'metavar': '<password>', 'short' : "p",
          'help': 'password to use to connect to the database',
          'default' : "maay",
          }),

        ('index-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 'i',
          'help': 'index this directory'
          }),
         
        ('skip-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 's',
          'help': 'skip this directory'
          }),
        ]

    config_file = 'indexer.ini'


def run():
    indexerConfig = IndexerConfiguration()
    indexerConfig.load()
    indexer = Indexer(indexerConfig)
    indexer.start()

if __name__ == '__main__':
    run()
