import StringIO
import sys
import re
import urlparse
import urllib

import maay.globalvars

import maay.converter.MaayHTMLParser
import maay.converter.texttools

import os.path

class HtmlToMaayHtmlParser(maay.converter.MaayHTMLParser.HTMLParser):
    def __init__(self, document_id, output, url):
        self.__output = output
        maay.converter.MaayHTMLParser.HTMLParser.__init__(self)
        self.__document_id = document_id
        self.__url = url
        
    def __rewrite_url(self, url):
        url_elements = urlparse.urlparse(url)

        self_url_elements = urlparse.urlparse(self.__url)
        new_url_elements = [self_url_elements[0], self_url_elements[1], self_url_elements[2], self_url_elements[3], self_url_elements[4], self_url_elements[5]]
        last_slash_pos = new_url_elements[2].rfind('/')
        if last_slash_pos > 0:
            new_url_elements[2] = new_url_elements[2][:last_slash_pos + 1]
    

        if not url_elements[1]:
            # we have a relative url...
            new_url_elements[2] = os.path.normpath(os.path.join(new_url_elements[2], url_elements[2])).replace('\\', '/')
            return urlparse.urlunparse(new_url_elements)
        return url
        

    def handle_starttag(self, tag, atts):
        self.__output.write("<%s" % tag)
        
        tag_lower = tag.lower()
        for var, val in atts:
            self.__output.write(" ")
            var_lower = var.lower()

            if (tag_lower, var_lower) in (("input", "src"), ("img", "src"), ("a", "href"), ("frame", "src"), ("link", "href"), ("script", "src"), ("table", "background"), ("body", "background"), ("area", "href"), ("form", "action")):
                val = self.__rewrite_url(val)

            self.__output.write('%s="%s"' % (var, val))

        self.__output.write(">")

    def handle_data(self, data):
#               print currentTag, data
#               print data
        self.__output.write(data)

    def handle_comment(self, data):
        self.__output.write("<!-- %s -->" % data)

    def handle_endtag(self, tag, atts):
        self.__output.write("</%s> " % tag)

    def handle_startendtag(self, tag, atts):
        self.__output.write("<%s" % tag)
        
        tag_lower = tag.lower()
        for var, val in atts:
            self.__output.write(" ")
            var_lower = var.lower()

            if (tag_lower, var_lower) in (("input", "src"), ("img", "src"), ("a", "href"), ("frame", "src"), ("link", "href"), ("script", "src"), ("table", "background"), ("body", "background"), ("area", "href"), ("form", "action")):
                val = self.__rewrite_url(val)

            self.__output.write('%s="%s"' % (var, val))

        self.__output.write(" />")


def htmlToMaayHtml(document_id, input, output, url = None):
    h = HtmlToMaayHtmlParser(document_id, output, url)
    while 1:
        data = input.read(1024)
        if not data:
            break
        h.feed(data)
    h.close()


#htmlToMaayHtml('DOCUMENT_ID', file('index.html', 'r'), sys.stdout)
#a = StringIO.StringIO()
#htmlToMaayHtml('DOCUMENT_ID', file('index.html', 'r'), a)
#print a.getvalue()

#print "title = %s" % h.getTitle()
#print texttools.stripWhiteSpaces(h.getText())
