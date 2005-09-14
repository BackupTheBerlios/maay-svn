"""This module contains the indexer code.
The indexer crawl files on disk, analyse the textual content
of a file and update the indexes.

TODO: analyse the God class into something understandable
"""

__revision__ = '$Id$'

import os, stat
from xmlrpclib import ServerProxy

from maay import converter
from maay.configuration import Configuration

class AuthenticationError(Exception):
    """raised when authentication on xmlrpc server failed"""

def getLastModificationTime(filename):
    return int(os.stat(filename)[stat.ST_MTIME])

def getFileSize(filename):
    return int(os.stat(filename)[stat.ST_SIZE])

class Indexer:
    def __init__(self, indexerConfig):
        self.indexerConfig = indexerConfig
        username = self.indexerConfig.user
        password = self.indexerConfig.password
        host = self.indexerConfig.host
        port = self.indexerConfig.port
        self.serverProxy = ServerProxy('http://%s:%s' % (host, port))
        self.cnxId = self.serverProxy.authenticate(username, password)
        if not self.cnxId:
            raise AuthenticationError("Failed to connect as '%s'" % username)
        
    def getFileIterator(self):
        indexed = self.indexerConfig.index_dir
        skipped = self.indexerConfig.skip_dir
        return FileIterator(indexed, skipped)

    def start(self):
        for filename in self.getFileIterator():
            lastModificationTime = getLastModificationTime(filename)
            lastIndexationTime = self.getLastModificationTime(filename)
            fileSize = getFileSize(filename)
            if lastIndexationTime == 0:
                # means never been indexed
                title, ttext = converter.extractWordsFromFile(filename)
                self.insertFileInformations(filename, title, text, fileSize, lastModificationTime)
            elif lastIndexationTime < lastModificationTime:
                # file has changed since last modification
                title, text = converter.extractWordsFromFile(filename)
                self.updateFileInformations(filename, title, text, fileSize, lastModificationTime)
            else:
                print "%s didn't change since last indexation"

    def fileWasModifiedSinceLastIndexation(self, filename):
        lastIndexationTime = self.serverProxy.lastIndexationTime(self.cnxId, filename)
        if lastIndexationTime is None:
            raise AuthenticationError("Bad cnxId sent to the server")
        return lastIndexationTime

    def updateFileInformations(self, filename, title, text):
        print "I should now update DB with all these new words ! (%s)" % filename
        
    def insertFileInformations(self, filename, title, text):
        print "I should now insert in DB with all these new words ! (%s)" % filename
    
        
class FileIterator:
    """provide a simple way to walk through indexed dirs"""
    def __init__(self, indexed, skipped=None):
        self.indexed = indexed
        self.skipped = skipped or []
        for dirpath in self.indexed:
            assert dirpath.startswith(os.path.sep), "relative paths not supported !"
        for dirpath in self.skipped:
            assert dirpath.startswith(os.path.sep), "relative paths not supported !"

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
          'help': 'identifier to use to connect to the database'}),

        ('password',
         {'type': 'string',
          'metavar': '<password>', 'short' : "p",
          'help': 'password to use to connect to the database'}),

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
