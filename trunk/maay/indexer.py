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

from maay.configuration import IndexerConfiguration
indexerConfig = IndexerConfiguration()
indexerConfig.load()


import os
import sys
import sha
from sets import Set
from xmlrpclib import ServerProxy, Fault, ProtocolError
import mimetypes
import socket

from zope.interface import Interface

from maay import converter
from maay.dbentity import FutureDocument, Document, FileInfo
from maay.querier import MaayAuthenticationError
from maay.texttool import removeControlChar
from threading import Thread
from twisted.python import log

class IIndexerObserver(Interface):

    def newDocumentIndexed(filename):
        """called by indexer when a document was just indexed"""

    def documentUntouched(filename):
        """called when a document was left untouched"""

    def indexationCompleted():
        """called when indexation is over"""


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


def safe_encode(string):
    """because string.encode('iso-8859-1', 'replace') is not safe"""
    if not isinstance(string, unicode):
        uni = string.decode('iso-8859-1', 'replace')
    else:
        uni = string
    res = uni.encode('iso-8859-1', 'replace')
    return res
        
        # type(filepath) = str 
        # filepath.encode('iso-8859-1', 'replace')
        #   passe implicitement pas un objet unicode
        #   Etape1: filepath.decode('', 'ignore') # <--- cette etape foire
        #   Etape2: filepath.encode() 



class FileIndexationFailure(Exception):

    def __init__(self, thefile, cause):
        self.thefile = thefile
        self.cause = cause

    def __str__(self):
        return "Won't index %s because %s" % (self.thefile,
                                              self.cause)

 
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
    
    def __init__(self, indexerConfig, observers=None):
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
        self.observers = observers or []
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
            indexed = self.indexerConfig.private_dir
            skipped = self.indexerConfig.skip_dir
            print "private indexation of", indexed, "omitting", skipped
        else:
            indexed = self.indexerConfig.public_dir[:]
            indexed.append(self.indexerConfig.download_dir)
            skipped = self.indexerConfig.skip_dir
            print "public indexation of", indexed, "omitting", skipped
        return FileIterator(indexed, skipped)

    def isIndexable(self, filename):
        return converter.isKnownType(filename)

    def purgeFiles(self,fileset):
        for filename in fileset:
            if self.verbose:
                print "Requesting unindexation of %s" % \
                      safe_encode(filename)
            self.serverProxy.removeFileInfo(self.cnxId, filename)
        if self.verbose:
            print "Requesting cleanup of unreferenced documents"
        self.serverProxy.removeUnreferencedDocuments(self.cnxId)

    def _purgeEverything(self):
        indexedFiles = Set(self.serverProxy.getIndexedFiles(self.cnxId))
        self.purgeFiles(indexedFiles)

    def start(self):
        # we index private dirs first because public overrides private
        # log.startLogging(open('maay-indexer.log', 'w'))
        existingFiles = self.runIndexer(isPrivate=True)
        existingFiles |= self.runIndexer(isPrivate=False)
        indexedFiles = Set(self.serverProxy.getIndexedFiles(self.cnxId))
        oldFiles = indexedFiles - existingFiles
        self.purgeFiles(oldFiles)
        for obs in self.observers:
            obs.indexationCompleted()

    def runIndexer(self, isPrivate=True):
        existingFiles = Set()
        state = docState(isPrivate)
        for filename in self.getFileIterator(isPrivate):
            existingFiles.add(filename)
            try:
                self.indexFile(filename, isPrivate)
            except FileIndexationFailure, fif: # should be catch-all
                print fif
                continue
        return existingFiles

    def indexFile(self, filepath, isPrivate=True):
        try:
            if not self.isIndexable(filepath):
                return
            state = docState(isPrivate)
            fileSize = os.path.getsize(filepath)
            lastModificationTime = os.path.getmtime(filepath)
            lastIdxTime, lastIdxState = self.getLastIndexationTimeAndState(filepath)
            if lastIdxState == state and lastIdxTime >= lastModificationTime:
                for obs in self.observers:
                    obs.documentUntouched(filepath)
                print "%s didn't change since last indexation" % (safe_encode(filepath),)
                return
            try:
                title, text, _, _ = converter.extractWordsFromFile(filepath)
            except converter.IndexationFailure, exc:
                raise FileIndexationFailure(safe_encode(filepath),
                                            "converter thus complained : %s" % exc)
            docId = makeDocumentId(filepath)
            mime_type = mimetypes.guess_type(filepath)[0]
            doc = FutureDocument(filename=filepath,
                                 title=title, text=text,
                                 fileSize=fileSize,
                                 lastModificationTime=lastModificationTime,
                                 content_hash=docId, mime_type=mime_type,
                                 state=state)
            self.indexDocument(doc)
        except FileIndexationFailure:
            raise
        except Exception, exc:
            raise FileIndexationFailure(safe_encode(filepath),
                                        "an exception %s was raised" % exc)                                        
       
    def getLastIndexationTimeAndState(self, filename):
        filename = filename
        answer = self.serverProxy.lastIndexationTimeAndState(self.cnxId, filename)
        if answer is None:
            raise MaayAuthenticationError("Bad cnxId sent to the Node")
        lastTime, lastState = answer
        return lastTime, lastState

    def indexDocument(self, futureDoc):
        futureDoc.file_state=FileInfo.CREATED_FILE_STATE
        if self.verbose:
            print "Requesting indexation of %s" % \
                  safe_encode(futureDoc.filename),
        try:
            futureDoc.title = removeControlChar(futureDoc.title) 
            futureDoc.text = removeControlChar(futureDoc.text)
            if self.verbose:
                print '('+safe_encode(futureDoc.title)+')'
            self.serverProxy.indexDocument(self.cnxId, futureDoc)

        except (Fault, ProtocolError), exc:
            if self.verbose:
                print "An error occured on the Node while indexing %s" % \
                      safe_encode(futureDoc.filename)
                print exc
                print "See Node log for details"
            else:
                print "Error indexing %s: %s" % \
                      (safe_encode(futureDoc.filename), exc)
        for obs in self.observers:
            obs.newDocumentIndexed(futureDoc.filename)

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
        self.indexed = [normalizeCase(p) for p in self.indexed]
        
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

def run(observers=None):
    try:
        try:
            indexer = Indexer(indexerConfig, observers=observers)
        except MaayAuthenticationError, exc:
            print "AuthenticationError:", exc
            sys.exit(1)
        indexer.start()
    except socket.error, exc:
        print "Cannot contact Node:", exc
        print "Check that the Node is running on %s:%s" % \
              (indexerConfig.host, indexerConfig.port)
        sys.exit(1)


## helpers for calls from the node, probably needs a serious fix

# run the indexer from webapp
indexer_thread = None
def _run_thread():
    global running
    running = True
    try:
        run()
    finally:    
        running = False

def is_running():
    print '** is_running()', indexer_thread
    return indexer_thread and indexer_thread.isAlive()

def start_as_thread(webpage):
    global indexer_thread
    if is_running():
        print "Indexer already running", indexer_thread
    else:
        print "launching indexer"
        indexer_thread = Thread(target=run, args=([webpage],))
        indexer_thread.start()

# index one file from webapp in a thread

def indexJustOneFile(filepath):
    thread = Thread(target=_just_one, args=(filepath,))
    thread.start()

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
        # log.startLogging(open('maay-indexer.log', 'w'))
        indexer.indexFile(filepath, isPrivate=False)
    except socket.error, exc:
        print "Cannot contact Node:", exc
        print "Check that the Node is running on %s:%s" % \
              (indexerConfig.host, indexerConfig.port)
    except FileIndexationFailure, fif:
        print fif

if __name__ == '__main__':
    run()


