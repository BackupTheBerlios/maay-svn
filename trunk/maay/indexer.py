#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

"""This module contains the indexer code.
The indexer crawl files on disk, analyse the textual content
of a file and update the indexes.

TODO: analyse the God class into something understandable
"""

__revision__ = '$Id$'

import os
import time
import sys
import sha
from sets import Set
from xmlrpclib import ServerProxy, Binary, Fault, ProtocolError
import mimetypes

from maay import converter
from maay.configuration import Configuration
from maay.dbentity import Document, FileInfo
from maay.querier import MaayAuthenticationError
from maay.texttool import removeControlChar

# grabbed from nevow
mimetypes.types_map.update(
    {
            '.conf':  'text/plain',
            '.diff':  'text/plain',
            '.exe':   'application/x-executable',
            '.flac':  'audio/x-flac',
            '.java':  'text/plain',
            '.ogg':   'application/ogg',
            '.oz':    'text/x-oz',
            '.swf':   'application/x-shockwave-flash',
            '.tgz':   'application/x-gtar',
            '.wml':   'text/vnd.wap.wml',
            '.xul':   'application/vnd.mozilla.xul+xml',
            '.py':    'text/plain',
            '.patch': 'text/plain',
            '.c' : 'text/plain',
            '.h': 'text/plain',
            '.C': 'text/plain',
            '.cpp': 'text/plain',
            '.cc': 'text/plain',
            '.c++': 'text/plain',
        }
    )


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
        self.serverProxy = ServerProxy('http://%s:%s' % (host, port),
                                       allow_none=True,
                                       encoding='utf-8')
        self.cnxId, errmsg = self.serverProxy.authenticate(username, password)
        self.verbose = indexerConfig.verbose
        if not self.cnxId:
            if self.verbose:
                print "Got failure from server:", errmsg
            raise MaayAuthenticationError("Failed to connect as '%s'" % username)
        
    def getFileIterator(self):
        indexed = self.indexerConfig.index_dir
        skipped = self.indexerConfig.skip_dir
        return FileIterator(indexed, skipped)

    def isIndexable(self, filename):
        return converter.isKnownType(filename)

    def start(self):
        existingFiles = Set()
        for filename in self.getFileIterator():
            existingFiles.add(filename)
            if not self.isIndexable(filename):
                continue
            lastModificationTime = os.path.getmtime(filename)
            lastIndexationTime = self.getLastIndexationTime(filename)
            if lastIndexationTime >= lastModificationTime:
                if self.verbose:
                    print "%s didn't change since last indexation" % filename
            else:
                fileSize = os.path.getsize(filename)
                try:
                    title, text, links, offset = converter.extractWordsFromFile(filename)
                except converter.IndexationFailure, exc:
                    if self.verbose:
                        print exc
                    continue
                docId = makeDocumentId(filename)
                mime_type = mimetypes.guess_type(filename)[0]

                self.indexDocument(filename, title, text, fileSize,
                                   lastModificationTime,
                                   docId, mime_type, Document.PUBLISHED_STATE)

        indexedFiles = Set(self.serverProxy.getIndexedFiles(self.cnxId))
        oldFiles = indexedFiles - existingFiles
        for filename in oldFiles:
            if self.verbose:
                print "Requesting unindexation of %s" % filename
            self.serverProxy.removeFileInfo(self.cnxId, filename)
        if self.verbose:
            print "Requesting cleanup of unreferenced documents"
        self.serverProxy.removeUnreferencedDocuments(self.cnxId)
        
    def getLastIndexationTime(self, filename):
        lastIndexationTime = self.serverProxy.lastIndexationTime(self.cnxId, filename)
        if lastIndexationTime is None:
            raise MaayAuthenticationError("Bad cnxId sent to the server")
        return lastIndexationTime

    def indexDocument(self, filename, title, text, fileSize,
                      lastModTime, content_hash, mime_type, state,
                      file_state=FileInfo.CREATED_FILE_STATE):
        if self.verbose:
            print "Requesting indexation of %s" % filename
        try:
            title = removeControlChar(title)
            text = removeControlChar(text)
            self.serverProxy.indexDocument(self.cnxId, filename, title, text,
                                           fileSize, lastModTime, content_hash,
                                           mime_type, state, file_state)
        except (Fault, ProtocolError), exc:
            if self.verbose:
                print "An error occured on the server while indexing %s" % filename.encode('iso-8859-1')
                print exc
                print "See server log for details"
            else:
                print "Error indexing %s: %s" % (filename.encode('iso-8859-1'), exc)
        
    
     
class FileIterator:
    """provide a simple way to walk through indexed dirs"""
    def __init__(self, indexed, skipped=None):
        self.indexed = [os.path.abspath(os.path.expanduser(p)) for p in indexed]
        skipped = skipped or []
        self.skipped = [os.path.abspath(os.path.expanduser(p)) for p in skipped]
        self.skipped = [self.normalizeCase(p) for p in self.skipped]
        
    if sys.platform == 'win32':
        def normalizeCase(self, path):
            return path.lower()
    else:    
        def normalizeCase(self, path):
            return path
        
    def __iter__(self):
        for path in self.indexed:
            # test path not in self.skipped (dummy config files)
            if path not in self.skipped:
                for dirpath, dirnames, filenames in os.walk(path):
                    self._removeSkippedDirnames(dirpath, dirnames)
                    try:
                        dirpath = unicode(dirpath, 'utf-8')
                    except UnicodeError:
                        dirpath = unicode(dirpath, 'iso-8859-1')
                    for filename in filenames:
                        try:
                            filename = unicode(filename, 'utf-8')
                        except UnicodeError:
                            filename = unicode(filename, 'iso-8859-1')
                        yield os.path.join(dirpath, filename)
                    
    def _removeSkippedDirnames(self, dirpath, dirnames):
        """removed skipped directories from dirnames (inplace !)"""
        for dirname in dirnames[:]:
            abspath = self.normalizeCase(os.path.join(dirpath, dirname))
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
        ('verbose',
         {'type': 'yn',
          'metavar': '<y or n>', 'short': 'v',
          'help': 'enable verbose mode',
          "default": False,
          }),
        ]

    config_file = 'indexer.ini'

    def __init__(self):
        Configuration.__init__(self, name="Indexer")

def run():
    indexerConfig = IndexerConfiguration()
    indexerConfig.load()
    try:
        indexer = Indexer(indexerConfig)
    except MaayAuthenticationError, exc:
        print "AuthenticationError:", exc
        sys.exit(1)
    indexer.start()

if __name__ == '__main__':
    run()
