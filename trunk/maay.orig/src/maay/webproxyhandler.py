"""
A great part of this code is taken from the Tiny HTTP Proxy from SUZUKI Hisao
"""

import signal
import socket
import urlparse
import SocketServer
import select
import re
import tempfile
import globalvars
import os
import time
import sha
import stat
import mimetypes

import converter.htmltomaayhtml
import maay.datastructure.documentinfo
import maay.datastructure.fileinfo

#class TimeoutError (Exception): pass

#def SIGALRM_handler(sig, stack): raise TimeoutError()
#signal.signal(signal.SIGALRM, SIGALRM_handler)

def connect_to(netloc, sock):              # throws TimeoutError
    proxy_host = globalvars.config.getValue("ProxyHost")
    proxy_port = globalvars.config.getValue("ProxyPort")
    if proxy_host:
        host = proxy_host
        port = proxy_port
    else:
        i = netloc.find(':')
        if i >= 0:
            host, port = netloc[:i], int(netloc[i+1:])
        else:
            host, port = netloc, 80
    print "\t" "connect to", host, port
#       signal.alarm(10)
    try:
        sock.connect((host, port))
#       finally:
#               signal.alarm(0)
    except Exception,e:
        print "connect_to: %s" % e



def handle_proxy_GET(httpRequestHandler, url = None):
    if not url:
        url = httpRequestHandler.path

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    (scm, netloc, path, params, query, fragment) = urlparse.urlparse(url, 'http')

#       print "PATH     =    %s" % url
#       print httpRequestHandler.headers
    if scm != 'http' or fragment or not netloc:
        httpRequestHandler.send_error(400, 'bad url %s' % url)
        return

    try:
        try:
            connect_to(netloc, sock)
        except TimeoutError:
            httpRequestHandler.send_error(504, "proxy has timed out")
            return
        except Exception, (code, message):
            httpRequestHandler.send_response(200)
            httpRequestHandler.end_headers()
            httpRequestHandler.wfile.write(globalvars.templateFile.getTemplateValue("page400", {'title': 'An error occured during request', 'message':message}))


        httpRequestHandler.log_request()
        str = '%s %s %s\r\n' % (
                httpRequestHandler.command, url,
#                       urlparse.urlunparse(('', '', path, params, query, '')),
                "HTTP/1.0")
#                       httpRequestHandler.request_version)
        print str

#               print "COMMANDE = %s" % str
#               print "PATH     =    %s" % url
        sock.send(str)
        httpRequestHandler.headers['Connection'] = 'close'
        del httpRequestHandler.headers['Proxy-Connection']
        del httpRequestHandler.headers['Accept-Encoding']

        # todo: handle gzipped page
        # with this del, the server understand that we do not handle gzip
        del httpRequestHandler.headers['Accept-Encoding']
        for (h, v) in httpRequestHandler.headers.items():
            str = '%s: %s\r\n' % (h, v)
            sock.send(str)
        sock.send('\r\n')
        return __read_write(httpRequestHandler, url, sock)
    finally:
        sock.close()
        httpRequestHandler.connection.close()
    return None

def __read_write(httpRequestHandler, url, sock, max_idling=20):
#

    rfile = httpRequestHandler.rfile

    last_modified = None
    date = None
    mime_type = None
    if hasattr(rfile, '_rbuf'):      # on BeOS?
        data = rfile._rbuf
    else:
        if httpRequestHandler.headers.has_key('Content-Length'):
            n = int(httpRequestHandler.headers['Content-Length'])
            data = rfile.read(n)
        else:
            httpRequestHandler.connection.setblocking(0)
            try: data = rfile.read()
            except IOError: data = ''
            httpRequestHandler.connection.setblocking(1)

    referer = httpRequestHandler.headers.get('Referer')
    rfile.close()
    if data:
        sock.send(data)

    iw = [httpRequestHandler.connection, sock]


    count = 0
    while 1:
        (ins, _, exs) = select.select(iw, [], iw, 3)
        count += 1
        if exs: break
        if ins:
            for i in ins:
                if i is sock:
                    out = httpRequestHandler.connection
                else:
                    out = sock
                data = i.recv(8192)
                if not data:
                    return
                httpRequestHandler.wfile.write(data)
            count = 0
#                       else:
#                               if count == max_idling:
#                                       break
#               return

def __read_index_write(httpRequestHandler, url, sock, max_idling=20):
    rfile = httpRequestHandler.rfile

    last_modified = None
    date = None
    mime_type = None
    if hasattr(rfile, '_rbuf'):      # on BeOS?
        data = rfile._rbuf
    else:
        if httpRequestHandler.headers.has_key('Content-Length'):
            n = int(httpRequestHandler.headers['Content-Length'])
            data = rfile.read(n)
        else:
            httpRequestHandler.connection.setblocking(0)
            try: data = rfile.read()
            except IOError: data = ''
            httpRequestHandler.connection.setblocking(1)

    referer = httpRequestHandler.headers.get('Referer')
    rfile.close()
    if data:
        sock.send(data)

    iw = [httpRequestHandler.connection, sock]


    count = 0
    headers = {}
    content = ""
    in_header = 2

    (f, tmpname) = tempfile.mkstemp(dir=globalvars.config.getValue('TemporaryDocumentRoot'))
    fd = os.fdopen(f, 'w')
    size = 0

    document_sha = sha.sha()

    while 1:
        count += 1
        (ins, _, exs) = select.select(iw, [], iw, 3)
        if exs: break
        if ins:
            for i in ins:
                if i is sock:
                    out = httpRequestHandler.connection
                else:
                    out = sock
                data = i.recv(8192)

                if not data:
                    continue

#                               httpRequestHandler.wfile.write(data)

                if in_header == 2:
                    start = 0
                    iter = re.finditer('\r\n', data)
                    while 1:
                        try:
                            match = iter.next()
                        except StopIteration:
                            break
                        header = data[start:match.start()]
                        start = match.end()

                        if in_header == 2:
                            httpRequestHandler.wfile.write(header + "\r\n")
                            in_header = 1
                            continue

                        if len(header) == 0:
                            in_header = 0

                            httpRequestHandler.wfile.write("\r\n")
                            data = data[start:]
                            fd.write(data)
                            document_sha.update(data)
                            size += len(data)
                            break

#                                               print "header = %s" % header

                        var, value = header.split(":", 1)
                        var = var.lower()
                        value = value.strip()

                        if var != 'content-length':
                            httpRequestHandler.wfile.write(header + "\r\n")

                        if var == 'last-modified':
                            last_modified = time.mktime(time.strptime(value, "%a, %d %b %Y %H:%M:%S %Z"))
                        elif var == 'content-type':
                            mime_type = value.split(";")[0].strip()
                        elif var == 'date':
                            date = time.mktime(time.strptime(value, "%a, %d %b %Y %H:%M:%S %Z"))
                else:
                    document_sha.update(data)
                    fd.write(data)
                    size += len(data)

                count = 0
        else:
            print "\t" "idle", count
        if count == max_idling: break

    fd.close()

    if size == 0:
        os.remove(tmpname)
        return

#               fileInfo = globalvars.database.getFileInfoByDocumentID(document_id)[0]
#               documentInfo = globalvars.database.getDocumentInfo(document_id)

#               httpRequestHandler.send_response(200)

#               httpRequestHandler.send_header('Content-Type', mime_type)
#               httpRequestHandler.send_header('Connection', 'close')
# TODO: send the date too
#               httpRequestHandler.send_header('Content-Length', os.stat(filename)[stat.ST_SIZE])
#               httpRequestHandler.send_header('Accept-Ranges', 'bytes')
#               httpRequestHandler.end_headers()

#       if mime_type == 'text/html':
#               fd = file(tmpname, 'r')
#               converter.htmltomaayhtml.htmlToMaayHtml(document_id, fd, httpRequestHandler.wfile, url)
#               fd.close()
#       else:
#               fd = file(tmpname, 'r')
#               while 1:
#                       data = fd.read(8192)
#                       if not data:
#                               break
#                       httpRequestHandler.wfile.write(data)
#               fd.close()
#
    document_id = document_sha.hexdigest()
    documentInfo = globalvars.database.getDocumentInfo(document_id)

    fd = file(tmpname, 'r')
    if mime_type == 'text/html':
        converter.htmltomaayhtml.htmlToMaayHtml(document_id, fd, httpRequestHandler.wfile, url)
    else:
        while 1:
            buffer = fd.read(4096)
            if not buffer:
                break
            httpRequestHandler.wfile.write(buffer)
    fd.close()
            

    if documentInfo and documentInfo.state in (maay.datastructure.documentinfo.PUBLISHED_STATE, maay.datastructure.documentinfo.CACHED_STATE):
        os.remove(tmpname)
        return

    last_modified = last_modified or date

    if mime_type == 'text/html':
        document_state = maay.datastructure.documentinfo.KNOWN_STATE
    else:
        document_state = maay.datastructure.documentinfo.CACHED_STATE

    if not documentInfo:
        globalvars.database.insertDocumentInfo(
                maay.datastructure.documentinfo.DocumentInfo(
                        document_id, 
                        mime_type, 
                        "", 
                        size, 
                        "", 
                        last_modified, 
                        document_state, 
                        0, 
                        url, 
                        0.0))

    newname = document_id + (mimetypes.guess_extension(mime_type) or ".txt")
    os.rename(tmpname, newname)
    file_time = int(os.stat(newname)[stat.ST_MTIME])
    fileInfo = maay.datastructure.fileinfo.FileInfo(
                    newname, 
                    file_time, 
                    document_id, 
                    maay.datastructure.documentinfo.CACHED_STATE, 
                    maay.datastructure.fileinfo.CREATED_FILE_STATE)

    globalvars.maay_core.completeNewLink(url, document_id)

    globalvars.indexer.addNewDocumentToIndex(globalvars.config.getValue("CachedDocumentRoot"), new_file_name)

    # addlink
#       print "----------------"
#       print "url = %s" % url
#       print "referer = %s" % referer
#       print "mime_type = %s" % mime_type
#       print "last_modified = %s" % last_modified
#       print "----------------"

#       if referer:
#               documentInfo = globalvars.database.getLastDocumentInfoByURL(url)
#               if documentInfo:
#                       linkinfo.LinkInfo(documentInfo.document_id, document_id)
#       print "content = %s" % content

