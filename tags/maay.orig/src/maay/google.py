"""
  Query Google and retrieve results from HTML response.
"""

import signal
import socket
import urlparse
import SocketServer
import cStringIO
import select
import re
import tempfile
import os
import time
import stat

import globalvars
import converter.MaayHTMLParser
import resultspool

#class TimeoutError (Exception): pass

#def SIGALRM_handler(sig, stack): raise TimeoutError()
#signal.signal(signal.SIGALRM, SIGALRM_handler)

def search(search_query, result_count):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    query_str = ""
    for w in search_query:
        query_str += "+" + w

    url = "http://www.google.com/search?q=%s&num=%s" % (query_str, result_count)

    proxy_host = globalvars.config.getValue("ProxyHost")
    proxy_port = globalvars.config.getValue("ProxyPort")
    if proxy_host:
        host = proxy_host
        port = proxy_port
    else:
        host = "www.google.com"
        port = 80

    try:
        try:
            print "\t" "connect to", host, port
#                       signal.alarm(10)
#                       try:
            sock.connect((host, port))
#                       finally:
#                               signal.alarm(0)
#               except TimeoutError:
#                       print "Time Out Error"
        except Exception, e:
            print "Exception %s" % e

        command = 'GET %s HTTP/1.0\r\n' % url

        # todo: handle gzipped page
        # with this del, the server understand that we do not handle gzip
#               for (h, v) in httpRequestHandler.headers.items():
#                       str = '%s: %s\r\n' % (h, v)
#                       sock.send(str)
        sock.send('%s\r\n' % command)
#               sock.send('Cookie: ID=7a08bece3317dd88:LD=en:NR=20:TM=1093852597:LM=1100792754:S=jv6Ek0k7UutKCXja\r\n')
#               sock.send("%s\r\nCookie: ID=7a08bece3317dd88:LD=en:NR=20:TM=1093852597:LM=1100792754:S=jv6Ek0k7UutKCXja\r\n\r\n" % command)

        data = sock.recv(10000)
        begin = 0
        end = 0
        while 1:
            begin = end
            end = data.find("\r\n", begin + 2)
            if end - begin == 2:
                break

        content = cStringIO.StringIO()
        content.write(data[end + 2:])
        while 1:
            data = sock.recv(10000)
            if not data:
                break
            content.write(data)

        parser = GoogleResultParser()
        parser.feed(content.getvalue())
        parser.close()
        return parser.get_results()


    finally:
        sock.close()
    return None

class GoogleResultParser(converter.MaayHTMLParser.HTMLParser):
    def __init__(self):
        converter.MaayHTMLParser.HTMLParser.__init__(self)
        self.__in_result = 0
        self.__result_title = ""
        self.__result_excerpt = ""
        self.__result_url = ""
        self.__results = []
        self.__description = ""

    def handle_starttag(self, tag, atts):
        tag_lower = tag.lower()

        if tag_lower == "p":
            for var, val in atts:
                if (var, val) == ("class", "g"):
                    if self.__in_result > 2:
                        size = -1
                        date = -1
                        descriptions = self.__description.split(" -  ")
                        print "descriptions = %s" % descriptions
                        if len(descriptions) > 1:
                            size_str = descriptions[1]
                            pos = re.search("^[0-9]+k$", size_str)
                            if pos and pos.start() == 0:
                                size = int(descriptions[1][:len(size_str) - 1]) * 1024
                                if len(descriptions) > 2:
                                    try:
                                        date = time.mktime(time.strptime(descriptions[2], "%d %b %Y"))
                                    except:
                                        pass

                        result = resultspool.SearchEngineResult(self.__result_title, self.__result_excerpt, self.__result_url, size, date)
                        self.__results.append(result)

                    self.__in_result = 1
                    self.__result_title = ""
                    self.__result_excerpt = ""
                    self.__result_url = ""




                    break
        elif self.__in_result == 1 and tag_lower == "a":
            for var, val in atts:
                if var == "href":
                    self.__result_url = val
            self.__in_result = 2
        elif self.__in_result == 2 and tag_lower in ("br", 'table'):
            self.__in_result = 3
        elif self.__in_result == 3 and tag_lower == 'br':
            self.__in_result = 4
        elif self.__in_result == 4 and tag_lower == 'font':
            self.__in_result = 5
            self.__description = ""
        elif self.__in_result == 5 and tag_lower == 'a':
            self.__in_result = 6
#                       self.__in_result = 
#                       result = resultspool.SearchEngineResult(self.__result_title, self.__result_excerpt, self.__result_url, 0, 0)
#                       self.__results.append(result)
#                       self.__in_result = 0

        
    def get_results(self):
        return self.__results

#       def handle_endtag(self, tag, atts):
#               tag_lower = tag.lower()
#               if self.__in_result == 2 and tag_lower == "a":
#                       self.__in_result = 3
#                       print "title : " + self.__result_title

    def handle_data(self, data):
        if self.__in_result == 2:
            self.__result_title += data
        elif self.__in_result == 3:
            self.__result_excerpt += data
        elif self.__in_result == 5:
            self.__description += data
#               print currentTag, data
#               print data
#               self.__out.write(data)

    def close(self):
        if self.__in_result > 0:
            result = resultspool.SearchEngineResult(self.__result_title, self.__result_excerpt, self.__result_url, 0, 0)
            self.__results.append(result)


