import threading
import mimetypes
import time
import signal
import thread
import socket
import sha
import tempfile
import os
import os.path


import maay.globalvars

#class TimeoutError (Exception): pass

#def SIGALRM_handler(sig, stack): raise TimeoutError()
#signal.signal(signal.SIGALRM, SIGALRM_handler)

class URLIndexer:
    def __init__(self, temporary_document_root, cached_document_root):
        self.__urls = []
        self.__lockUrls = threading.Lock()
        self.__temporary_document_root = temporary_document_root
        self.__cached_document_root = cached_document_root
        self.__run = 0

    def insertURL(self, url, search_query, weight):
        self.__lockUrls.acquire()
        self.__urls.append((url, search_query, weight))
        self.__lockUrls.release()

    def startIndexCycleProcess(self):
        thread.start_new_thread(self.__indexCycleProcess, ())

    # TODO: call this method in maay.py
    def stopIndexCycleProcess(self):
        self.__run = 0


    def __indexCycleProcess(self):
        self.__run = 1
        while self.__run:
            self.__lockUrls.acquire()
            if len(self.__urls) > 0:
                url, search_query, weight = self.__urls.pop()
            else:
                url = None
            self.__lockUrls.release()

            if url:
                tmp_filename = tempfile.mktemp("", maay.globalvars.config.getValue("TemporaryDocumentRoot") + os.path.sep)
                fd = file(tmp_filename, "wb")

                infos = self.__fetchURL(url, fd)

                if infos:
                    mime_type, last_modified, content_size, document_id = infos
                else:
                    continue

                newname = document_id + (mimetypes.guess_extension(mime_type) or ".txt")
                absolute_newname = "%s%s%s" % (maay.globalvars.config.getValue("CachedDocumentRoot"), os.path.sep, newname)
                if os.path.exists(absolute_newname):
                    os.remove(absolute_newname)

                maay.globalvars.logger.debug("rename %s => %s" % (tmp_filename, absolute_newname))
                os.rename(tmp_filename, absolute_newname)
                maay.globalvars.logger.debug("done => %s" % absolute_newname)
                maay.globalvars.indexer.addNewDocumentToIndex(absolute_newname, mime_type, last_modified, url, search_query=search_query, weight=weight)
            else:
                time.sleep(2)
        

    def __fetchURL(self, url, output):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        proxy_host = maay.globalvars.config.getValue("ProxyHost")
        proxy_port = maay.globalvars.config.getValue("ProxyPort")
        if proxy_host:
            host = proxy_host
            port = proxy_port
        else:
            (scm, netloc, path, params, query, fragment) = urlparse.urlparse(url, 'http')
            l = netloc.split(":")
            host = l[0]
            if len(l) == 2:
                port = int(l[1])
            else:
                port = 80

        try:
            try:
                print "\t" "connect to", host, port
#                               signal.alarm(10)
#                               try:
                sock.connect((host, port))
#                               finally:
#                                       signal.alarm(0)
            except TimeoutError:
                print "Time Out Error"
            except Exception, e:
                print "Exception %s" % e

            command = 'GET %s HTTP/1.0\r\n' % url

            sock.send('%s\r\n' % command)

            content_length = 0

            data = sock.recv(10000)
            begin = 0
            end = -2
            mime_type = None
            last_modified = int(time.time())
            content_length = -1
            while 1:
                begin = end + 2
                end = data.find("\r\n", begin)
                line = data[begin:end]
                if end - begin == 0:
                    break

                print line
                # first line is HTTP/1.0 200 OK
                # TODO: handle redirection...
                if begin == 0:
                    words = line.split()
                    if words[1] != '200':
                        maay.globalvars.logger.exception("%s not fetched : code %s returned!" % (url, words[1]))
                        sock.close()
                        return None
                        
        
                l = line.split(":", 1)
                if len(l) != 2:
                    continue
                var = l[0].lower()
                val = l[1].strip()
                if var == "content-type":
                    mime_type = val.split(";", 1)[0]
                if var == "last-modified":
                    print "val = *%s*"% val
                    last_modified = int(time.mktime(time.strptime(val, "%a, %d %b %Y %H:%M:%S %Z")))
                    print "last modified = %s (%d)" % (val, last_modified)
                if var == "content-length":
                    print "content length = %d" % int(val)
                    content_length = int(val)

            s = sha.sha()
            data = data[end + 2:]
            output.write(data)
            s.update(data)

            content_size = len(data)

            while 1:
                data = sock.recv(10000)
                if not data:
                    break

                s.update(data)
                content_size += len(data)
                output.write(data)
#                       print content.getvalue()
            output.close()
        except:
            sock.close()
            maay.globalvars.logger.exception("")
            return None
    
        sock.close()
        maay.globalvars.logger.debug("%s fetched !" % url)
        return (mime_type, last_modified, content_size, s.hexdigest())


