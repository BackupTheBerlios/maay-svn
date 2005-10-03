# for the moment, support only ONE connection at the time for each file downloaded
# TODO: multisource
import signal
import os
import httplib
import stat
import time
import mimetypes

import globalvars
import protocol
import constants
import response
import maay.datastructure.fileinfo
import maay.datastructure.documentinfo
import download

#class TimeoutError (Exception): pass
#def SIGALRM_handler(sig, stack): raise TimeoutError()

#signal.signal(signal.SIGALRM, SIGALRM_handler)

NOT_STARTED_STATE = 0
INIT_STATE = 1
FINISHED_STATE = 2
SEARCHING_SOURCES_STATE = 3
WAITING_STATE = 4
CONNECTING_STATE = 5
DOWNLOADING_STATE = 6
NEXT_RETRY_PERIOD = 10
NEXT_SEARCH_PERIOD = 30

class Download:

    FINISHED_STATE = 2

    def __init__(self, document_id, search_query = []):
        self.__active = 0
        self.__providers = []
        self.__providersHT = {}
        self.__document_id = document_id
        self.__search_query = search_query
        self.__transferred = 0
        self.__state = download.NOT_STARTED_STATE
        self.__last_search_time = 0
        # TODO: for the moment unisource is ok
        # divide the file into chunks of 256ko
        # several states : in download, downloaded, not downloaded

    def isActive(self):
        return self.__active

    def setActive(self, active):
        self.__active = active

    def fetch(self):
        if self.__state == download.FINISHED_STATE:
            return 1

        if self.__state == download.NOT_STARTED_STATE:
            self.__state = download.INIT_STATE
        while 1:
            documentInfo = globalvars.database.getDocumentInfo(self.__document_id)
            documentProviders = globalvars.database.getDocumentProviders(documentInfo.db_document_id)
            for dp in documentProviders:
                p = self.__providersHT.get(dp.node_id)
                if p:
                    n = globalvars.database.getNodeInfo(dp.node_id)
                    if p.ip != n.ip or p.port != n.port:
                        p.port = port
                        p.ip = ip
                        p.state = download.Provider.UNTRIED_STATE
                        p.last_try = 0
                else:
                    n = globalvars.database.getNodeInfo(dp.node_id)
                    p = download.Provider(n.node_id, n.ip, n.port, n.bandwidth, dp.last_providing_time)
                    self.__providers.append(p)
                    self.__providersHT[dp.node_id] = p

            provider = None
            for p in self.__providers:
                if p.state in (download.Provider.UNREACHABLE_STATE, download.Provider.NOT_PROVIDING_STATE):
                    continue
                if p.last_try + download.NEXT_RETRY_PERIOD > time.time():
                    continue
                provider = p
                break

            if not provider:
                print "no provider"
                if self.__last_search_time + download.NEXT_SEARCH_PERIOD > time.time() and self.__state == download.SEARCHING_SOURCES_STATE:
                    time.sleep(1)
                    return 0

                globalvars.maay_core.send_search_request(["#%s" % self.__document_id], constants.INIT_TTL, constants.MAAY_SEARCH_RANGE, constants.MIN_SCORE, constants.INIT_FNC, constants.INIT_EHC, query_id = self.__document_id)
                print "search for providers"
                self.__state = download.SEARCHING_SOURCES_STATE
                self.__last_search_time = time.time()
                time.sleep(1)
                return 0

            print "PROVIDER IP =%s [%s]" % (provider.ip, provider.state)

            self.__state = download.CONNECTING_STATE
            provider.state = download.Provider.CONNECTED_STATE
            connection = None
            try:
#                               signal.alarm(5)
                print "essaie sur %s %s" % (provider.ip, provider.port)
                connection = httplib.HTTPConnection(provider.ip, provider.port)
                connection.putrequest("POST", "/message")
                connection.endheaders()
#                               signal.alarm(0)
            except Exception, e:
#                               signal.alarm(0)
                print "Exception: %s" % e
                provider.state = download.Provider.UNREACHABLE_STATE
                continue
            except TimeoutError:
#                               signal.alarm(0)
                provider.state = download.Provider.BUSY_STATE
                provider.last_try = time.time()
                continue
            try:
                provider.state = download.Provider.DOWNLOADING_STATE
                protocol.sendHeader(connection, constants.DOWNLOAD_REQUEST_COMMAND, "12345678901234567890", constants.INIT_TTL)
                protocol.sendDownloadRequest(connection, self.__document_id, self.__search_query)
                print "requete envoye, attente reponse %s" % connection

                r = connection.getresponse()
                print "resp"

                (protocol_version, vendor, node_id, ip, port, bandwidth, counter, command_type, queryID, TTL) =  response.readHeader(r)
                print "resp 2"

                document_id, flags = response.readDownloadResponse(r)
                if not (flags & constants.HAS_DOCUMENT_DESCRIPTION_FLAG):
                    print "the provider do not have the file %s" % len(self.__providers)
                    provider.state = download.Provider.NOT_PROVIDING_STATE
                    globalvars.database.deleteDocumentProvider(db_document_id = documentInfo.db_document_id, node_id = provider.node_id)
                    continue

                (title, publication_time, mime_type, size, url, provider_count) = response.readDownloadResponseDocumentDescription(r)
                print "url received = %s" % url
                globalvars.maay_core.updateDocumentInfo(document_id, mime_type, title, size, publication_time, url)

                
                for j in xrange(provider_count):
                    (node_id, ip, port, last_storing_time, last_seen_time, bandwidth, counter) = response.readSearchResponseHitProvider(r)
                    print "provider in resp = %s" % str((node_id, ip, port, bandwidth, counter, last_seen_time))
                    globalvars.maay_core.updateNodeInfo(node_id, ip, port, bandwidth, counter, last_seen_time)
                    globalvars.maay_core.updateDocumentProvider(documentInfo.db_document_id, node_id, last_storing_time)
                    globalvars.maay_core.manifest_interest(node_id, self.__search_query)

                if not (flags & constants.HAS_DOCUMENT_CONTENT_FLAG):
                    print "the provider do not have the file %s" % len(self.__providers)
                    provider.state = download.Provider.NOT_PROVIDING_STATE
                    globalvars.database.deleteDocumentProvider(db_document_id = documentInfo.db_document_id, node_id = provider.node_id)
                    continue


                content_input = response.readDownloadResponseInput(r)

                self.__state = download.DOWNLOADING_STATE
                print "waiting document content"

                file_name = globalvars.config.getValue("TemporaryDocumentRoot") + os.path.sep + document_id + (mimetypes.guess_extension(mime_type) or ".txt")
                fd = file(file_name, "wb")

                idle = 0
                self.__transferred = 0

                while self.__transferred < size and idle < 20:
                    idle += 1
                    buf = content_input.read(1024)
                    if not buf:
                        continue
                    idle = 0
                    fd.write(buf)
#                                       print "write buf"
                    self.__transferred += len(buf)
                fd.close()
                if idle > 20:
                    raise "idle"

                print "document received completeley"

                if self.__transferred != size:
                    print "Error: file length not match %s %s" % (self.__transferred, size)
                    connection.close()
                    os.remove(file_name)
                    continue

                new_file_name = document_id + (mimetypes.guess_extension(mime_type) or ".txt")
                absolute_new_file_name = "%s%s%s" % (globalvars.config.getValue("CachedDocumentRoot"), os.path.sep, new_file_name)
                if os.path.exists(absolute_new_file_name):
                    os.remove(absolute_new_file_name)

                print "rename %s => %s" % (file_name, absolute_new_file_name)
                os.rename(file_name, absolute_new_file_name)
                print "done => %s" % absolute_new_file_name
#                               file_time = int(os.stat(absolute_new_file_name)[stat.ST_MTIME])
                file_time = 0
                fileInfo = maay.datastructure.fileinfo.FileInfo(absolute_new_file_name, file_time, documentInfo.db_document_id, maay.datastructure.documentinfo.CACHED_STATE, maay.datastructure.fileinfo.CREATED_FILE_STATE)
                print "1 documentInfo.db_document_id = %s" %   fileInfo.db_document_id
                db_fileInfos = globalvars.database.getFileInfos(file_name=absolute_new_file_name)
                if not db_fileInfos:
                    globalvars.database.insertFileInfo(fileInfo)
                else:
                    globalvars.database.updateFileInfo(fileInfo)

                globalvars.indexer.addNewDocumentToIndex(absolute_new_file_name)

                self.__state = download.FINISHED_STATE
                provider.state = download.Provider.FINISHED_STATE
                return 1

            except Exception, e:
                time.sleep(2)

#                       else:
#                       except TimeoutError, e:
                print "Error ex: %s" % e
                provider.state = download.Provider.BUSY_STATE
                provider.last_try = time.time()

#                       connection.close()

        print "finish"
        return 0

#       def start(self):
#               thread.start_new_thread(self.__run, ())
#               self.__run()

    def getLastSearchTime(self):
        return 

    def getState(self):
        return self.__state

    def getStateStr(self):
        if self.__state == download.INIT_STATE:
            return 'Initialisation'
        elif self.__state == download.FINISHED_STATE:
            return 'Download finished'
        elif self.__state == download.SEARCHING_SOURCES_STATE:
            next_retry = int(download.NEXT_SEARCH_PERIOD - (time.time() - self.__last_search_time))
            if next_retry > 0:
                return 'Searching sources... (next retry in %s s)' % next_retry
            else:
                return 'Searching sources...'
        elif self.__state == download.WAITING_STATE:
            return 'Waiting %s seconds before searching sources...' % int(download.NEXT_SEARCH_PERIOD - (time.time() - self.last_try))
        elif self.__state == download.CONNECTING_STATE:
            return 'Connecting...'
        elif self.__state == download.DOWNLOADING_STATE:
            return 'Downloading...'
        elif self.__state == download.NOT_STARTED_STATE:
            return 'Not started...'


    def getDocumentID(self):
        return self.__document_id

    def getTransferred(self):
        return self.__transferred
#       def getState

    def getProviders(self):
        return self.__providers

class Provider:
    UNTRIED_STATE = 1
    CONNECTED_STATE = 2
    DOWNLOADING_STATE = 3
    UNREACHABLE_STATE = 4
    NOT_PROVIDING_STATE = 5
    BUSY_STATE = 6
    FINISHED_STATE = 7

    def __init__(self, node_id, ip, port, bandwidth, last_providing_time):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.bandwidth = bandwidth
        self.last_providing_time = last_providing_time
        self.state = download.Provider.UNTRIED_STATE
        self.last_try = 0

#       def setState(self, state):
#               self.__state = state
    def getStateStr(self):
        print "self.state = %s" % self.state
        if self.state == download.Provider.UNTRIED_STATE:
            return "Untried"
        elif self.state == download.Provider.BUSY_STATE:
            return "Busy"
        elif self.state == download.Provider.CONNECTED_STATE:
            return "Connecting..."
        elif self.state == download.Provider.DOWNLOADING_STATE:
            return "Downloading..."
        elif self.state == download.Provider.UNREACHABLE_STATE:
            return "Unreachable..."
        elif self.state == download.Provider.NOT_PROVIDING_STATE:
            return "Not provide file"
        elif self.state == download.Provider.FINISHED_STATE:
            return "Finished"


