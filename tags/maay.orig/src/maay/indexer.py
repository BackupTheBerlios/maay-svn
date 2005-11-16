# This module contains the indexer code.
# The indexer crawl files on disk, analyse the textual content of a file and update the indexes.
# TODO: analyse the God class into something understandable

import os
import re
import sys
import time
import stat
import threading
import thread
import time
import mimetypes

import maay.datastructure.documentscore
import maay.datastructure.fileinfo
import maay.datastructure.documentprovider
import maay.datastructure.documentinfo
import maay.globalvars
import maay.constants
import maay.tools
import maay.converter.htmltotext
import maay.converter.texttotext


PUBLISHED_INDEXATION = 0
PRIVATE_INDEXATION = 1

class Indexer:
    # TODO: remove last arguments...
    def __init__(self, indexedDirectories, notIndexedDirectories, publishedDirectories, notPublishedDirectories, publishedDocumentRoot, cachedDocumentRoot, lastIndexedPrivateFilename, lastIndexedPublishedFilename):
        self.__indexedDirectories = indexedDirectories
        self.__notIndexedDirectories = notIndexedDirectories
        self.__publishedDirectories = publishedDirectories
        self.__notPublishedDirectories = notPublishedDirectories

        self.publishedDocumentRoot = publishedDocumentRoot
        self.cachedDocumentRoot = cachedDocumentRoot
        self.__documentsToIndex = []
        self.__stop_indexer = 0
        self.__priority = maay.constants.LOW_PRIORITY
        self.__current_file_name = None


        self.__publishedFileCrawler = maay.globalvars.FileCrawlerClass(indexedDirectories, notIndexedDirectories, publishedDirectories, notPublishedDirectories, [  ], [  ], PUBLISHED_INDEXATION, self.__isIndexable)
        self.__privateFileCrawler  = maay.globalvars.FileCrawlerClass(indexedDirectories, notIndexedDirectories, publishedDirectories, notPublishedDirectories,  [ ] , [  ], PRIVATE_INDEXATION, self.__isIndexable)

        self.__lastIndexedPrivateFilename = lastIndexedPrivateFilename
        self.__lastIndexedPublishedFilename = lastIndexedPublishedFilename
        
        self.__publishedReindexationWhenFinished = False
        self.__privateReindexationWhenFinished = False

        self.__pauseTime = 0
        self.__pausePeriod = 0
        
        self.__indexing_idle = False
        self.__stopLock = threading.Lock()

        self.__pausePeriod = 0
        
        self.__firstIndexingTime = 1

        self.__publishedIndexerMutex = threading.Lock()
        self.__privateIndexerMutex = threading.Lock()

        self.__publishedDocumentFileIndexer = DocumentFileIndexer(self.__publishedFileCrawler, maay.datastructure.documentinfo.PUBLISHED_STATE)
        self.__privateDocumentFileIndexer = DocumentFileIndexer(self.__privateFileCrawler, maay.datastructure.documentinfo.PRIVATE_STATE)
        
    def getLastIndexedPrivateFilename(self):
        return self.__lastIndexedPrivateFilename

    def getIndexedDirectories(self):
        return self.__indexedDirectories

    def getNotIndexedDirectories(self):
        return self.__notIndexedDirectories

    def getPublishedDirectories(self):
        return self.__publishedDirectories

    def getNotPublishedDirectories(self):
        return self.__notPublishedDirectories
        
    def setIndexedDirectories(self, indexedDirectories):
        self.__indexedDirectories = indexedDirectories
        self.__publishedFileCrawler.setIndexedDirectories(indexedDirectories)
        self.__privateFileCrawler.setIndexedDirectories(indexedDirectories)
        
    def setNotIndexedDirectories(self, notIndexedDirectories):
        self.__notIndexedDirectories = notIndexedDirectories
        self.__publishedFileCrawler.setNotIndexedDirectories(notIndexedDirectories)
        self.__privateFileCrawler.setNotIndexedDirectories(notIndexedDirectories)

    def setPublishedDirectories(self, publishedDirectories):
        self.__publishedDirectories = publishedDirectories
        self.__publishedFileCrawler.setPublishedDirectories(publishedDirectories)
        self.__privateFileCrawler.setPublishedDirectories(publishedDirectories)
        

    def setNotPublishedDirectories(self, notPublishedDirectories):
        self.__notPublishedDirectories = notPublishedDirectories
        self.__publishedFileCrawler.setNotPublishedDirectories(notPublishedDirectories)
        self.__privateFileCrawler.setNotPublishedDirectories(notPublishedDirectories)
        
    # pause for 15 minutes.
    def pause(self):
        self.__pauseTime = time.time()
        self.__pausePeriod += 15 * 60

    # return True if indexer is paused, else False.
    def isPaused(self):
        return time.time() < self.__pauseTime + self.__pausePeriod

    # resume from pause
    def resume(self):
        self.__pauseTime = time.time()
        self.__pausePeriod = 0

    def a(self):
        try:
            self.__indexRepository()
        except:
            maay.globalvars.logger.exception("indexrepos")

    # start indexation process cycle        
    def startIndexCycleProcess(self):
#               thread.start_new_thread(self.__indexRepository, ())
        thread.start_new_thread(self.a, ())

    # stop indexation process cycle 
    def stopIndexCycleProcess(self):
        self.__stop_indexer = 1

        try:
            self.__waitingNewDocumentLock.release()
        except:
            pass
        try:
            self.__indexingPolicyMutex.release()
        except:
            pass
        self.__stopLock.acquire()
        try:
            self.__stopLock.release()
        except:
            pass

    # set priority of indexer (for debug purpose only)
    def setPriority(self, priority):
        self.__priority = priority

    # get priority of indexer (for debug purpose only)
    def getPriority(self):
        return self.__priority
        

        
    def __indexRepository(self):
        finish_published_indexation = 0
        self.__stopLock.acquire()

#               if self.__lastIndexedPrivateFilename:
#                       self.__privateFileCrawler.reset(self.__lastIndexedPrivateFilename)
                
#               if self.__lastIndexedPublishedFilename:
#                       self.__publishedFileCrawler.reset(self.__lastIndexedPublishedFilename)

        maay.globalvars.logger.debug("Start Full Indexation")
                                
        while True:
            # if indexer is stopped, leave the indexation loop
            if self.__stop_indexer == 1:
                try:
                    self.__stopLock.release()
                except:
                    pass
                return
                
            # idle to not take too much process time
#                       self.__interDocumentIdle()
            time.sleep(1)

            # the indexer index in priority:
            #       - cached documents (downloaded documents)
            #       - published documents
            #       - private documents
            try:
                # index downloaded files (cached) if any
                while True:
                    if len(self.__documentsToIndex) == 0:
                        filename = None
                        break                                           
                    filename, mime_type, last_modified, url, search_query, weight = self.__documentsToIndex.pop()
                    if self.__isIndexable(filename):
                        break

                if filename:
                    self.indexDocument(filename, maay.datastructure.documentinfo.CACHED_STATE, mime_type=mime_type, publication_time=last_modified, url=url)
                    if search_query:
                        fileInfo = maay.globalvars.database.getFileInfos(file_name=filename)[0]
                        documentInfo = maay.globalvars.database.getDocumentInfos(db_document_id=fileInfo.db_document_id)[0]
                        maay.globalvars.maay_core.hasDownloaded(maay.globalvars.maay_core.getNodeID(), documentInfo.document_id, search_query, weight=weight)
                    continue
                                            
                # index published files if any
                self.__publishedIndexerMutex.acquire()
                work = False
                try:
                    work = self.__publishedDocumentFileIndexer.next()
                except:
                    maay.globalvars.logger.exception("failed to index publish")
                self.__publishedIndexerMutex.release()

                if work:
                    continue
                elif self.__publishedReindexationWhenFinished == True:
                    self.__publishedReindexationWhenFinished = False
                    self.__publishedDocumentFileIndexer.reset()
                    continue

                # index cached files if any                             
                self.__privateIndexerMutex.acquire()
                work = False
                try:
                    work = self.__privateDocumentFileIndexer.next() 
                except:
                    maay.globalvars.logger.exception("failed to index private")
                    maay.globalvars.logger.debug("about to index %s" % (self.__privateDocumentFileIndexer.filename,))
                self.__privateIndexerMutex.release()
                
                if not work:
                    # TODO: faire un lock à la place de ça...
                    # nothing to do:
                    # => sleep
                    if self.__privateReindexationWhenFinished:
                        self.__privateReindexationWhenFinished = False
                        self.__privateDocumentFileIndexer.reset()
                        continue

                    time.sleep(1)

            except:
                maay.globalvars.logger.exception("indexRepository")

    # Remove file reference in database.
    def removeFileInfo(self, fileInfo):
        maay.globalvars.database.deleteFileInfos(file_name=fileInfo.file_name)
        self.checkDocumentState(fileInfo.db_document_id)

    # Check the state of the document reference in database.
    # Used after a file removal, a download, ...
    def checkDocumentState(self, db_document_id):
        fileInfos = maay.globalvars.database.getFileInfos(db_document_id = db_document_id)
        documentInfos = maay.globalvars.database.getDocumentInfos(db_document_id = db_document_id)
        if not documentInfos:
            return
        documentInfo = documentInfos[0]

        if len(fileInfos) == 0:
            if documentInfo.state == maay.datastructure.documentinfo.PRIVATE_STATE:
                maay.globalvars.database.deleteDocumentInfos(db_document_id=documentInfo.db_document_id)
            else:
                documentInfo.state = maay.datastructure.documentinfo.KNOWN_STATE
                maay.globalvars.database.updateDocumentInfo(documentInfo)
        else:
            state = fileInfos[0].state
            if state != maay.datastructure.documentinfo.PUBLISHED_STATE:
                for fileInfo in fileInfos[1:]:
                    if state == maay.datastructure.documentinfo.CACHED_STATE and fileInfo.state in (maay.datastructure.documentinfo.PUBLISHED_STATE):
                        state = fileInfo.state
                    elif state == maay.datastructure.documentinfo.PRIVATE_STATE and fileInfo.state in (maay.datastructure.documentinfo.CACHED_STATE, maay.datastructure.documentinfo.PUBLISHED_STATE):
                        state = fileInfo.state                                          
                    elif state == maay.datastructure.documentinfo.KNOWN_STATE:
                        state = fileInfo.state
            maay.globalvars.database.updateDocumentInfo(documentInfo)

    # Return True if published indexation is finished.
    def isPublishedIndexationFinished(self):
        return self.__publishedDocumentFileIndexer.isFinished()

    # Return True if private indexation is finished.
    def isPrivateIndexationFinished(self):
        return self.__privateDocumentFileIndexer.isFinished()

    def forcePublishedReindexationWhenFinished(self):
        self.__publishedReindexationWhenFinished = True

    def forcePrivateReindexationWhenFinished(self):
        self.__privateReindexationWhenFinished = True
        
    # Force published reindexation before the next period of published reindexation.
    def forcePublishedIndexation(self):
        self.__publishedIndexerMutex.acquire()
        if self.__publishedDocumentFileIndexer.isFinished():
            self.__publishedDocumentFileIndexer.reset()
        self.__publishedIndexerMutex.release()          


    # Force private reindexation before the next period of published reindexation.
    def forcePrivateIndexation(self):
        self.__privateIndexerMutex.acquire()
        if self.__privateDocumentFileIndexer.isFinished():
            self.__privateDocumentFileIndexer.reset()
        self.__privateIndexerMutex.release()

    # Idle document indexing.
    def __interDocumentIdle(self):
        while not self.__stop_indexer:
            if not self.isPaused():
                break
            self.__indexing_idle = True
            time.sleep(2)
        self.__indexing_idle = True
        maay.globalvars.maay_core.idle(self.__priority)
        self.__indexing_idle = False


    # Return true if indexer is idle.
    def isIdle(self):
        return self.__indexing_idle

    # Return the current file being indexed.
    def getCurrentFileName(self):
        return self.__current_file_name

    # Return true if the file is indexable (right mime_type)
    def __isIndexable(self, filename):
            
        # discard filenames that start with "." (TODO: a matter of
        # policy that probably does not belong here at all)

        basename = os.path.basename(filename)
        if basename[0] == ".": return False

        # does this file have a converter ?

        mime_type = mimetypes.guess_type(filename)[0]
        conv = maay.globalvars.converterFile.get_converter(mime_type)
        if conv: return True
                
        return False

    # Index document
    def indexDocument(self, file_name, document_state, publication_time = None, mime_type = None, url = None, fileInfo = None):
        try:
            self.__current_file_name = file_name

            if not self.__isIndexable(file_name): return False
            
            maay.globalvars.logger.info("Checking %s:" % file_name)

            file_time = int(os.stat(file_name)[stat.ST_MTIME])
            if not fileInfo:
                fileInfos = maay.globalvars.database.getFileInfos(file_name = file_name)
                if len(fileInfos) == 0:
                    fileInfo = None
                else:
                    fileInfo = fileInfos[0]

            doc_size = 0

            if fileInfo:
                # check if the document_state of the file has changed (e.g. change from private to published)
                if fileInfo.state != document_state:
                    fileInfo.state = document_state
                    maay.globalvars.database.updateFileInfo(fileInfo)
                    self.checkDocumentState(fileInfo.db_document_id)

                # if exists compare the file time indexed
                if fileInfo.file_time == file_time:
                    maay.globalvars.logger.debug("skipped [same timestamp]")
                    return

                f = file(file_name, 'rb')
                content = f.read()
                f.close()
                document_id = maay.tools.maay_hash(content)
                doc_size = len(content)

                documentInfo = maay.globalvars.database.getDocumentInfo(document_id=document_id)

                if not documentInfo or (not documentInfo.indexed) or documentInfo.db_document_id != fileInfo.db_document_id:
                    # the file has to be reindexed
                    self.removeFileInfo(fileInfo)
                    fileInfo = None
                else:
                    if (document_state in (maay.datastructure.documentinfo.PUBLISHED_STATE, maay.datastructure.documentinfo.CACHED_STATE) and documentInfo.state == maay.datastructure.documentinfo.PRIVATE_STATE) or (document_state == maay.datastructure.documentinfo.PUBLISHED_STATE and documentInfo.state == maay.datastructure.documentinfo.CACHED_STATE):
                        documentInfo.state = document_state
                        maay.globalvars.database.updateDocumentInfo(fileInfo)

                    fileInfo.file_time = file_time
                    maay.globalvars.database.updateFileInfo(fileInfo)
                    maay.globalvars.logger.debug("skipped [same sha1]")
                    return


            if not fileInfo:
                # TODO: optimize this part
                f = file(file_name, 'rb')
                content = f.read()
                f.close()
                document_id = maay.tools.maay_hash(content)
                doc_size = len(content)

            # check if we have to index the file or not

            documentInfo = maay.globalvars.database.getDocumentInfo(document_id=document_id)
            if documentInfo and documentInfo.indexed:               
                self.checkDocumentState(documentInfo.db_document_id)
                maay.globalvars.logger.debug("already indexed, skipped indexation !")
                return

            documentScores = {}
            wrong_file = 0
            mime_type = mimetypes.guess_type(file_name)[0]
            conv = maay.globalvars.converterFile.get_converter(mime_type)
            if conv.command != 'None':
                output_file_name = os.path.normpath("%s%s%s" % (maay.globalvars.config.getValue("TemporaryDocumentRoot"), os.path.sep, document_id))
                command = conv.command.lstrip('"')
                command = command.rstrip('"')
                pos = command.find("$in")
                # buggy re.sub that convert \\ into \
                if pos != -1:
                    command = '%s"%s"%s' % (command[:pos], file_name, command[pos + 3:])
                pos = command.find("$out")
                if pos != -1:
                    command = '%s"%s"%s' % (command[:pos], output_file_name, command[pos + 4:])
                # TODO: echeck error code
                maay.globalvars.logger.debug(command)
                code = maay.globalvars.command.execute(command)
                if code == 256:
                    wrong_file = 1
                temporary_file = output_file_name
            else:
                temporary_file = None
                output_file_name = file_name

            if wrong_file == 0:
                try:
                    fd = file(output_file_name, 'rb')
                    content = fd.read()
                    fd.close()
                except IOError, e:
                    maay.globalvars.logger.debug("read error : %s" % e)
                    wrong_file = 1

            if wrong_file == 1:
                # does the content of the file change (comparing sha1) ?
    #                       document_id = sha.sha(file(absolute_file_name, 'r').read()).hexdigest()
                if not fileInfo:
                    fileInfo = maay.datastructure.fileinfo.FileInfo(file_name, file_time, -1, document_state, maay.datastructure.fileinfo.NOT_INDEXED_FILE_STATE)
                    maay.globalvars.database.insertFileInfo(fileInfo)
                else:
                    fileInfo.db_document_id = documentInfo.db_document_id
                    fileInfo.file_state = maay.datastructure.fileinfo.NOT_INDEXED_FILE_STATE
                    fileInfo.state = document_state
                    maay.globalvars.database.updateFileInfo(fileInfo)

                maay.globalvars.logger.debug("not indexable")
                return


            if conv.dst_type == "html":
                title, text_content, links = maay.converter.htmltotext.htmlToText(content)
                offset = len(title) + 1
                indexed_content = title + " " + text_content
            elif conv.dst_type == "text":
                title, text_content = maay.converter.texttotext.textToText(content)
                indexed_content = text_content
                links = []
                offset = 0
            else:
                raise "Strange, dst type not conform %s" % conv.dst_type
                # just add a document entry in the documents table

            if not indexed_content:
                maay.globalvars.logger.debug("Strange : no content")
    #                       return None


            db_text_content = text_content[:maay.constants.MAX_TEXT_CONTENT_STORED_SIZE]
            if not publication_time:
                publication_time = file_time


            if not documentInfo:
                documentInfo = maay.datastructure.documentinfo.DocumentInfo(None, document_id, mime_type, title, doc_size, db_text_content, publication_time, maay.datastructure.documentinfo.UNKNOWN_STATE, 1, url, 0, 1)
                maay.globalvars.database.insertDocumentInfo(documentInfo)
            else:
                documentInfo.title = title
                documentInfo.text = db_text_content
                documentInfo.download_count = 1
                documentInfo.indexed = 1
                documentInfo.state = maay.datastructure.documentinfo.UNKNOWN_STATE
                if url:
                    documentInfo.url = url

                maay.globalvars.database.updateDocumentInfo(documentInfo)

            # parsing words

            iter = re.finditer('([a-zA-Z0-9]|%s)+' % maay.globalvars.accent.getRegularExpression(), indexed_content)

            while 1:
                try:
                    match = iter.next()
                except StopIteration:
                    break

                word = indexed_content[match.start():match.end()]

                if len(word) < maay.constants.MIN_WORD_SIZE or len(word) >= maay.constants.MAX_WORD_SIZE:
                    continue


                word = word.lower()
                word = maay.globalvars.accent.translate(word)

                position = match.start() - offset
                if position < 0:
                    position = -1

                if not documentScores.has_key(word):
                    documentScores[word] = maay.datastructure.documentscore.DocumentScore(documentInfo.db_document_id, word, position, 0, 0, 0)
                elif documentScores[word].position == -1:
                    documentScores[word].position = position

            if indexed_content:
                documentInfo.download_count = 0
                # add the sha1 of the document as a keyword of the document
                documentScores["#%s" % document_id] = maay.datastructure.documentscore.DocumentScore(documentInfo.db_document_id, "#%s" % document_id, 0, 0, 0, 0)

    #                       maay.globalvars.database.insertDocumentScores(documentScores.values())
                db_documentScoresHT = maay.globalvars.database.getDocumentScoresHT(db_document_id = documentInfo.db_document_id)
                for word, ds in documentScores.items():
                    db_documentScore = db_documentScoresHT.get(word)
                    if db_documentScore:
                        ds.download_count = db_documentScore.download_count
                        documentInfo.download_count += ds.download_count

                        maay.globalvars.database.updateDocumentScore(ds)
    #                                       ds.relevance = db_documentScores[word]
    #                                       ds.popularity = db_documentScores[word]
    #                                       maay.globalvars.database.updateDocumentScore(ds)
                    else:
                        try:
                            maay.globalvars.database.insertDocumentScore(ds)
                        except Exception, e:
                            maay.globalvars.logger.debug("warning %s" % (str(e)))
        #                                       maay.globalvars.database.updateDocumentScore(ds)

            documentInfo.state = document_state
            maay.globalvars.database.updateDocumentInfo(documentInfo)

            if not fileInfo:
                # does the content of the file change (comparing sha1) ?
    #                       document_id = sha.sha(file(absolute_file_name, 'r').read()).hexdigest()
                fileInfo = maay.datastructure.fileinfo.FileInfo(file_name, file_time, documentInfo.db_document_id, document_state, maay.datastructure.fileinfo.CREATED_FILE_STATE)
                maay.globalvars.database.insertFileInfo(fileInfo)
            else:
                fileInfo.db_document_id = documentInfo.db_document_id
                maay.globalvars.database.updateFileInfo(fileInfo)

            provider = maay.globalvars.database.getDocumentProvider(documentInfo.db_document_id, maay.globalvars.maay_core.getNodeID())
            if not provider:
                provider = maay.datastructure.documentprovider.DocumentProvider(documentInfo.db_document_id, maay.globalvars.maay_core.getNodeID(), int(time.time()))
                maay.globalvars.database.insertDocumentProvider(provider)
            else:
                provider.last_providing_time = int(time.time())
                maay.globalvars.database.updateDocumentProvider(provider)


            if temporary_file:
                os.remove(temporary_file)

            maay.globalvars.maay_core.updateDocumentMatching(document_id=document_id)
    
        except:
            maay.globalvars.logger.debug("failed to index %s" % file_name)

            
    def addNewDocumentToIndex(self, file_name, mime_type = None, last_modified = None, url = None, search_query=None, weight=None):
        self.__documentsToIndex.insert(0, (file_name, mime_type, last_modified, url, search_query, weight))



class DocumentFileIndexer:
    def __init__(self, fileCrawler, state):
        self.__db_fileInfos = None
        self.__db_fileInfosCount = 0
        self.__db_fileInfosPosition = 0
        self.__db_fileInfosEOF = False
        self.__fileCrawler = fileCrawler
        self.__state = state
        self.__finished = False
        self.__db_lastFileName = None

    def reset(self):
        self.__db_fileInfos = None
        self.__db_fileInfosCount = 0
        self.__db_fileInfosPosition = 0
        self.__db_fileInfosEOF = False
        self.__db_lastFileName = None
        self.__finished = False
        self.__fileCrawler.reset()

    def isFinished(self):
        return self.__finished

    def next(self):
        if self.__finished:
            return False
    
        filename = self.__fileCrawler.getNextFilename()
        print "filename = %s" %filename
        # DELETEME
        self.filename = filename

        # then search in the database a fileInfo with a filename greater (ascii sense)
        # then the filename of the file on disk. (fileInfo that are lesser than
        # the filename of the file are removed files...
        while True:             

            if not self.__db_fileInfosEOF and self.__db_fileInfosPosition >= self.__db_fileInfosCount:
                self.__db_fileInfos = maay.globalvars.database.getFileInfos(state = self.__state, order_by_filename=1, file_name_sup = self.__db_lastFileName, limit=(0, 1000))
                if len(self.__db_fileInfos) == 0:
                    self.__db_fileInfosEOF = True
                else:
                    self.__db_fileInfosCount = len(self.__db_fileInfos)
                    self.__db_lastFileName = self.__db_fileInfos[self.__db_fileInfosCount - 1].file_name
                    self.__db_fileInfosPosition = 0
                # to let some idle time

            if not self.__db_fileInfosEOF:
                fileInfo = self.__db_fileInfos[self.__db_fileInfosPosition]
            else:
                fileInfo = None
#                       print "fileInfo = %s / %s (%s)" % (fileInfo and fileInfo.file_name, filename, self.__db_lastFileName)
            if fileInfo and (filename == None or fileInfo.file_name.upper() < filename.upper()):
                # that means, that we have a file in the database, that is
                # not on the disk => the file has been removed (or is not indexable...) !
                # so remove it !
                maay.globalvars.logger.debug( "file removed = %s" % fileInfo.file_name)
                maay.globalvars.indexer.removeFileInfo(fileInfo)
                self.__db_fileInfosPosition += 1
            else:
                break

        if filename:
            if fileInfo and filename == fileInfo.file_name:
                self.__db_fileInfosPosition += 1
                maay.globalvars.indexer.indexDocument(filename, self.__state, fileInfo=fileInfo)
            else:
                maay.globalvars.indexer.indexDocument(filename, self.__state)
            return True
        else:
            self.__finished = True
            print "indexation terminee"
            return False    
