import thread
import threading
import time
import traceback
import sys

import download
import globalvars
import downloadmanager
import constants

class DownloadManager:
    def __init__(self):
        self.__downloads = []
        self.__downloadByDocumentID = {}
        self.__counter = 0
        self.__activeDownloadCount = 0
        self.__mutex = threading.Lock()

    def getInactiveDownload(self):
        self.__mutex.acquire()
        c = self.__activeDownloadCount 
        self.__mutex.release()
        if c >= globalvars.max_simultaneous_download:
            return None

        self.__mutex.acquire()
        for i in range(0, len(self.__downloads)):
            if self.__counter >= len(self.__downloads):
                self.__counter = 0
            download = self.__downloads[self.__counter]
            self.__counter += 1
            if download.isActive():
                continue
            download.setActive(1)
            self.__activeDownloadCount += 1
            self.__mutex.release()
            return download

        self.__mutex.release()
        return None

    def start(self):
        for i in range(0, 1):
            downloader = downloadmanager.Downloader()
            downloader.start()

    def insertDownload(self, document_id, search_query):
        if self.__downloadByDocumentID.has_key(document_id):
            return

        self.__mutex.acquire()
        print "insert le download"
        dl = download.Download(document_id, search_query)
        self.__downloadByDocumentID[document_id] = dl
        self.__downloads.append(dl)
        self.__mutex.release()

    def cancelDownload(self, document_id):
        download = self.__downloadByDocumentID.get(document_id)
        if download:
            self.__downloads.remove(download)
            del self.__downloadByDocumentID[document_id]
            self.__mutex.acquire()
            self.__activeDownloadCount -= 1
            self.__mutex.release()


    def getDownloads(self):
        return self.__downloads

    def getDownload(self, document_id):
        return self.__downloadByDocumentID[document_id]
        
    def __start_download(self, download):
        if not download.fetch():
            download.setActive(0)
        self.__mutex.acquire()
        self.__activeDownloadCount -= 1
        self.__mutex.release()

    def __run(self):
        while 1:
#                       try:
            time.sleep(2)
            download = self.getInactiveDownload()
#                               print "download = %s" % download
            if not download:
                continue

            try:
                thread.start_new_thread(self.__start_download, (download,))
            except Exception, e:
                print "exception: %s" % e

#                               if not download.fetch():
#                       except Exception, e:
#                               print "exception %s" %e

                                
    def start(self):
        thread.start_new_thread(self.__run, ())
#               self.__run()

    def stop(self):
        pass

