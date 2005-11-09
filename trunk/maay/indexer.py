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
import socket

import maay.indexer
from maay import converter
from maay.configuration import Configuration
from maay.dbentity import FutureDocument, Document, FileInfo
from maay.querier import MaayAuthenticationError
from maay.texttool import removeControlChar
from thread import start_new_thread

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
        self.filesystemEncoding = sys.getfilesystemencoding()
        print "Indexer connecting to server %s:%s" % (host, port)
        self.serverProxy = ServerProxy('http://%s:%s' % (host, port),
                                       allow_none=True,
                                       encoding='utf-8')
        self.cnxId, errmsg = self.serverProxy.authenticate(username, password)
        self.verbose = indexerConfig.verbose
        if not self.cnxId:
            if self.verbose:
                print "Got failure from server:", errmsg
            raise MaayAuthenticationError("Failed to connect as '%s'" % username)
        # we might be asked to purge everything and just exit
        if indexerConfig['purge']:
            self._purgeEverything()
            sys.exit(0)
            
        
    def getFileIterator(self, isPrivate=True):
        if isPrivate:
            indexed = self.indexerConfig.private_index_dir
            skipped = self.indexerConfig.private_skip_dir
            print "private indexation of", indexed, "omitting", skipped
        else:
            indexed = self.indexerConfig.public_index_dir
            skipped = self.indexerConfig.public_skip_dir
            print "public indexation of", indexed, "omitting", skipped
        return FileIterator(indexed, skipped)

    def isIndexable(self, filename):
        return converter.isKnownType(filename)

    def purgeFiles(self,fileset):
        for filename in fileset:
            if self.verbose:
                print "Requesting unindexation of %s" % filename
            self.serverProxy.removeFileInfo(self.cnxId,
                                            unicode(filename,
                                                    self.filesystemEncoding))
        if self.verbose:
            print "Requesting cleanup of unreferenced documents"
        self.serverProxy.removeUnreferencedDocuments(self.cnxId)

    def _purgeEverything(self):
        indexedFiles = Set(self.serverProxy.getIndexedFiles(self.cnxId))
        self.purgeFiles(indexedFiles)

    def start(self):
        # we index private dirs first because public overrides private
        existingFiles = self.runIndexer(isPrivate=True)
        existingFiles |= self.runIndexer(isPrivate=False)
        indexedFiles = Set(self.serverProxy.getIndexedFiles(self.cnxId))
        oldFiles = indexedFiles - existingFiles
        self.purgeFiles(oldFiles)

    def runIndexer(self, isPrivate=True):
        existingFiles = Set()
        
        if isPrivate:
            state = Document.PRIVATE_STATE
        else:
            state = Document.PUBLISHED_STATE
            
        for filename in self.getFileIterator(isPrivate):
            existingFiles.add(filename)
            if not self.isIndexable(filename):
                continue
            lastModificationTime = os.path.getmtime(filename)
            lastIdxTime, lastIdxState = self.getLastIndexationTimeAndState(filename)
            if lastIdxState == state and lastIdxTime >= lastModificationTime:
                if self.verbose:
                    print "%s didn't change since last indexation" % filename
                continue
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

                self.indexDocument(FutureDocument(filename=unicode(filename,
                                                                   self.filesystemEncoding),
                                                  title=title, text=text,
                                                  fileSize=fileSize,
                                                  lastModificationTime=lastModificationTime,
                                                  content_hash=docId, mime_type=mime_type,
                                                  state=state))
        return existingFiles
        
    def getLastIndexationTimeAndState(self, filename):
        filename = unicode(filename, self.filesystemEncoding)
        answer = self.serverProxy.lastIndexationTimeAndState(self.cnxId, filename)
        if answer is None:
            raise MaayAuthenticationError("Bad cnxId sent to the server")
        lastTime, lastState = answer
        return lastTime, lastState

    def indexDocument(self, futureDoc):
        futureDoc.file_state=FileInfo.CREATED_FILE_STATE
        if self.verbose:
            print "Requesting indexation of %s" % futureDoc.filename,
        try:
            futureDoc.title = removeControlChar(futureDoc.title) 
            futureDoc.text = removeControlChar(futureDoc.text)
            if self.verbose:
                print '('+futureDoc.title.encode('utf-8')+')'
            self.serverProxy.indexDocument(self.cnxId, futureDoc)

        except (Fault, ProtocolError), exc:
            if self.verbose:
                print "An error occured on the server while indexing %s" % \
                      futureDoc.filename.encode('iso-8859-1')
                print exc
                print "See server log for details"
            else:
                print "Error indexing %s: %s" % (futureDoc.filename.encode('iso-8859-1'), exc)
        

class FileIterator:
    """provide a simple way to walk through indexed dirs"""
    def __init__(self, indexed, skipped=[]):
        assert((type(indexed) in (list, tuple)) and
               (type(skipped) in (list,tuple)))
        self.indexed = [os.path.abspath(os.path.expanduser(p)) for p in indexed]
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
                    print "looking in", dirpath
                    self._removeSkippedDirnames(dirpath, dirnames)
                    for filename in filenames:
                        if os.access(os.path.join(dirpath, filename), os.R_OK): 
                            yield os.path.join(dirpath, filename)
                    
    def _removeSkippedDirnames(self, dirpath, dirnames):
        """removed skipped directories from dirnames (inplace !)"""
        for dirname in dirnames[:]:
            abspath = self.normalizeCase(os.path.join(dirpath, dirname))
            if abspath in self.skipped:
                # print "skipping", dirname
                dirnames.remove(dirname)




## main() ##################################################

class IndexerConfiguration(Configuration):
    options = Configuration.options + [
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

        ('private-index-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 'i',
          'help': 'index this directory with the private indexer',
          'default' : []
          }),
         
        ('private-skip-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 's',
          'help': 'the private indexer will skip this directory',
          'default' : []
          }),
        ('public-index-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 'I',
          'help': 'index this directory with the public indexer',
          'default' : []
          }),
         
        ('public-skip-dir',
         {'type': 'csv',
          'metavar': '<csv>', 'short': 'S',
          'help': 'the public indexer will skip this directory',
          'default' : []
          }),

        ('verbose',
         {'type': 'yn',
          'metavar': '<y or n>', 'short': 'v',
          'help': 'enable verbose mode',
          "default": False,
          }),
        ('purge',
         {'type' : 'yn',
          'help' : 'purge the set of indexed documents and returns immediately',
          'metavar' : '<y or n>',
          'default' : False,
          }),
        ]

    config_file = 'indexer.ini'

    def __init__(self):
        Configuration.__init__(self, name="Indexer")


def run():
    indexerConfig = IndexerConfiguration()
    indexerConfig.load()
    try:
        try:
            indexer = Indexer(indexerConfig)
        except MaayAuthenticationError, exc:
            print "AuthenticationError:", exc
            sys.exit(1)
        indexer.start()
    except socket.error, exc:
        print "Cannot contact server:", exc
        print "Check that the server is running on %s:%s" % \
              (indexerConfig.host, indexerConfig.port)
        sys.exit(1)

running = False

def _run_thread():
    maay.indexer.running = True
    try:
        run()
    finally:    
        maay.indexer.running = False

def start_as_thread():
    if maay.indexer.running:
        print "Indexer already running"
        return
    start_new_thread(_run_thread, ())

if __name__ == '__main__':
    run()


