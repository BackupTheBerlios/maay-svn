#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""This module contains the indexer code.
The indexer crawl files on disk, analyse the textual content
of a file and update the indexes.

TODO: analyse the God class into something understandable
"""

__revision__ = '$Id$'

import os
import sys
import sha
from sets import Set
from xmlrpclib import ServerProxy, Fault, ProtocolError
import mimetypes
import socket

import maay.indexer
from maay import converter
from maay.configuration import IndexerConfiguration
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

def docState(privateness):
    """from boolean to Document internal special state"""
    if privateness:
        state = Document.PRIVATE_STATE
    else:
        state = Document.PUBLISHED_STATE
    return state
    
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
        print "Indexer connecting to Node %s:%s" % (host, port)
        self.serverProxy = ServerProxy('http://%s:%s' % (host, port),
                                       allow_none=True,
                                       encoding='utf-8')
        self.cnxId, errmsg = self.serverProxy.authenticate(username, password)
        self.verbose = indexerConfig.verbose
        if not self.cnxId:
            if self.verbose:
                print "Got failure from Node:", errmsg
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
            indexed.append(self.indexerConfig.download_index_dir)
            skipped = self.indexerConfig.public_skip_dir
            print "public indexation of", indexed, "omitting", skipped
        return FileIterator(indexed, skipped)

    def isIndexable(self, filename):
        return converter.isKnownType(filename)

    def purgeFiles(self,fileset):
        for filename in fileset:
            if self.verbose:
                print "Requesting unindexation of %s" % filename
            self.serverProxy.removeFileInfo(self.cnxId, filename)
            #XXX: fix by alf, below, causes indexer crash on auc personnal machine
##                                             unicode(filename,
##                                                     self.filesystemEncoding))
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
        
        state = docState(isPrivate)
        for filename in self.getFileIterator(isPrivate):
            existingFiles.add(filename)
            self.indexFile(filename, isPrivate)
        return existingFiles

    def indexFile(self, filepath, isPrivate=True):
        if not self.isIndexable(filepath):
            if self.verbose:
                print "Indexer indexFile : can't index %s" % filepath
            return

        state = docState(isPrivate)
        fileSize = os.path.getsize(filepath)
        lastModificationTime = os.path.getmtime(filepath)
        lastIdxTime, lastIdxState = self.getLastIndexationTimeAndState(filepath)
        if lastIdxState == state and lastIdxTime >= lastModificationTime:
            if self.verbose:
                print "%s didn't change since last indexation" % filepath
                return
        try:
            title, text, _, _ = converter.extractWordsFromFile(filepath)
        except converter.IndexationFailure, exc:
            if self.verbose:
                print exc
            return
        docId = makeDocumentId(filepath)
        mime_type = mimetypes.guess_type(filepath)[0]
        doc = FutureDocument(filename=unicode(filepath,
                                              self.filesystemEncoding),
                             title=title, text=text,
                             fileSize=fileSize,
                             lastModificationTime=lastModificationTime,
                             content_hash=docId, mime_type=mime_type,
                             state=state)
        self.indexDocument(doc)
       
    def getLastIndexationTimeAndState(self, filename):
        filename = unicode(filename, self.filesystemEncoding)
        answer = self.serverProxy.lastIndexationTimeAndState(self.cnxId, filename)
        if answer is None:
            raise MaayAuthenticationError("Bad cnxId sent to the Node")
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
                print "An error occured on the Node while indexing %s" % \
                      futureDoc.filename.encode('iso-8859-1')
                print exc
                print "See Node log for details"
            else:
                print "Error indexing %s: %s" % (futureDoc.filename.encode('iso-8859-1'), exc)
        

######### FileIterator

if sys.platform == 'win32':
    def normalizeCase(path):
        return path.lower()
else:    
    def normalizeCase(path):
        return path

class FileIterator:
    """provide a simple way to walk through indexed dirs"""
    def __init__(self, indexed, skipped=[]):
        assert((type(indexed) in (list, tuple)) and
               (type(skipped) in (list,tuple)))
        self.indexed = [os.path.abspath(os.path.expanduser(p)) for p in indexed]
        self.skipped = [os.path.abspath(os.path.expanduser(p)) for p in skipped]
        self.skipped = [normalizeCase(p) for p in self.skipped]
        
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
            abspath = normalizeCase(os.path.join(dirpath, dirname))
            if abspath in self.skipped:
                # print "skipping", dirname
                dirnames.remove(dirname)

## main() ##################################################

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
        print "Cannot contact Node:", exc
        print "Check that the Node is running on %s:%s" % \
              (indexerConfig.host, indexerConfig.port)
        sys.exit(1)

running = False

## helpers for calls from the node, probably needs a serious fix

# run the indexer from webapp

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

# index one file from webapp

def indexJustOneFile(filepath):
    start_new_thread(_just_one, (filepath,))

def _just_one(filepath):
    indexerConfig = IndexerConfiguration()
    indexerConfig.load()
    try:
        try:
            indexer = Indexer(indexerConfig)
        except MaayAuthenticationError, exc:
            print "AuthenticationError:", exc
            return
        print 'going to index file %s', filepath
        indexer.indexFile(filepath, isPrivate=False)
    except socket.error, exc:
        print "Cannot contact Node:", exc
        print "Check that the Node is running on %s:%s" % \
              (indexerConfig.host, indexerConfig.port)

if __name__ == '__main__':
    run()


