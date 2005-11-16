"""Module <webserver>: webserver

This module implements all the functions for the web server and all the
dynamic pages used for the front end of maay.

The WebServerHandler dispatches the task to :
- webinterfacehandler : dynamic page shown through browser
- messagehandler : message received from other maay nodes (search request/response)
- maaywebcachehandler : maaywebcache request (ask for a list of maay nodes)
"""

import os
import stat
import httplib
import thread
import BaseHTTPServer, SocketServer
import urlparse
import cgi
import re
import socket
import math
import time

import constants
import response
import globalvars

import webserver
import webinterfacehandler
import messagehandler
import webproxyhandler
import maaywebcachehandler


class WebServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_GET(self):
        globalvars.maay_core.suspend_low_priority_tasks()
        try:
            """ This function is called for each HTTP GET on the maay web server."""
            global templateFile, current_result_spool_query_id

            u = urlparse.urlparse(self.path)
            # check if it is a local request: /index.html or remote: http://www.google.com
            globalvars.logger.debug(u)
            if u[0] != 'http' or (u[1], u[2]) == ('localhost', globalvars.config.getValue('Port')):
                if u[2] == '/message':
                    messagehandler.handleMessage(self)
                elif u[2] == '/maaywebcache':
                    maaywebcachehandler.handle_get(self)
                else:
                    webinterfacehandler.handle_get(self)
                    
            # in the case it is used as a proxy                                             
            elif u[0] == 'http' and len(u[1]) != 0: 
                if (u[2] == '/maay/document'):
                    error = 0
                    args = cgi.parse_qs(u[4])
                    if args.get('did'):
                        document_id = args.get('did')[0]
                    else:
                        error = 1
                    if args.get('nid'):
                        node_id = args.get('nid')[0]
                    else:
                        error = 1

                    if error:
                        # TODO: show an error message
                        raise Exception("Bad did or nid in document parameter")
                        
                    us = u[1].split(':')
                    if len(us) == 1:
                        ip = us[0]
                        port = 80
                    else:
                        ip = us[0]
                        port = int(us[1])

                    globalvars.maay_core.updateNodeInfo(node_id, ip, port, 0, 0, 0)
                    globalvars.maay_core.updateDocumentProvider(document_id, node_id, 0)
                    globalvars.maay_core.updateDocumentInfo(document_id, "", "", "", 0, "", state = documentinfo.UNKNOWN_STATE)

                    url = "http://localhost:%s/maay/docframe?did=%s" % (globalvars.config.getValue('Port'), document_id)
                    print "send download request"
                    self.send_response(301)
                    self.send_header('Location', url)
                    print "header = %s"% url
                    self.end_headers()
    #                                       webinterfacehandler.__get_document_frame(self, document_id,None)
    
                else:
                    webproxyhandler.handle_proxy_GET(self)
            else:
                print "------------------------"
                print "CASE UNCAPTURED, FIX THIS"
                print "------------------------"
        except Exception, e:
#               except ImportError, e:
            print "Webserver error: %s" % e
            globalvars.logger.exception("Webserver error: %s" % e)
            globalvars.maay_core.resume_low_priority_tasks()
    

    do_HEAD = do_GET
    do_POST = do_GET
    do_PUT = do_GET
    do_DELETE = do_GET

class WebServer(BaseHTTPServer.HTTPServer, SocketServer.ThreadingMixIn,SocketServer.TCPServer):
    def __init__(self, port):
        self.port = port
        server_address = ('', self.port)
        BaseHTTPServer.HTTPServer.__init__(self, server_address, WebServerHandler)
    def start(self):
#               thread.start_new_thread(self.__run, ())
        self.__run()

    def __run(self):
        while 1:
            request = self.get_request()
            SocketServer.ThreadingMixIn.process_request(self, request[0], request[1])
            self.handle_request()
#                       self.process_request(request[0], request[1])
#                       thread.start_new_thread(BaseHTTPServer.HTTPServer.process_request)
#                       thread.start_new_thread(SocketServer.ThreadingMixIn.process_request, (self, request[0], request[1]))


class WebServerError (Exception): pass

def __runWebServer(port, d, n, t):
    global document_root, maay_core, templateFile

    document_root = d
    maay_core = n

    templateFile = t

    try:
        ws = webserver.WebServer(port)
    except socket.error, e:
        raise WebServerError(e[1])
    ws.start()

def runWebServer(port, d, n, t):
    thread.start_new_thread(__runWebServer, (port, d, n, t))

