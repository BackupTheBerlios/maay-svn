import urlparse
import cStringIO

import MaayHTMLParser
import htmltools
import texttools

class MyHTMLParser(MaayHTMLParser.HTMLParser):
    def __init__(self):
        MaayHTMLParser.HTMLParser.__init__(self)
        self.__tagStack = []
        self.__title = None
#               self.__text = ""
        self.__text = cStringIO.StringIO()
        self.__links = []

    def handle_starttag(self, tag, atts):
#               print "start = %s" % tag
        self.__tagStack.insert(0, tag.lower())

        tag_lower = tag.lower()
        for var, val in atts:
            var_lower = var.lower()
            if (tag_lower, var_lower) in (("img", "src"), ("a", "href"), ("frame", "src"), ("link", "href"), ("script", "src"), ("table", "background"), ("body", "background"), ("area", "href")):
                # it is relative url, we rewrite the url with the form :
                # http://localhost:8000/document?did=*********
                # remove bookmark in page (e.g. http://www.toto.com/index.html#titi)
                if not val:
                    url = ""
                else:
                    url_elements = urlparse.urlparse(val)
                    url = urlparse.urlunparse((url_elements[0], url_elements[1], url_elements[2], url_elements[3], url_elements[4], ''))

#                               if url_elements[0] == '':
                    # TODO: check if we can use heap because of uniqness
#                               if not url_elements[2] in self.__links:
#                                       self.__links.append(url_elements[2])
                if not url in self.__links:
                    self.__links.append(url)



    def handle_data(self, data):
        if len(self.__tagStack) == 0:
            return


        currentTag =  self.__tagStack[0].lower()
        if currentTag == 'title':
            self.__title = htmltools.htmlToText(data)
        elif not currentTag in ('style', 'script', 'title'):
            self.__text.write(" ")
            data = texttools.stripWhiteSpaces(data) or ""
            data = data.strip()

            data = htmltools.htmlToText(data)
            self.__text.write(data)

    def handle_endtag(self, tag, atts):
        i = 0
        tag = tag.lower()
        while i < len(self.__tagStack) and self.__tagStack[i] != tag:
            i += 1

        if i < len(self.__tagStack):
            self.__tagStack = self.__tagStack[i + 1:]

    def handle_startendtag(self, tag, atts):
        pass

    def getTitle(self):
        return self.__title

    def getText(self):
        return self.__text.getvalue()

    def getLinks(self):
        return self.__links


def htmlToText(data = None, input = None):
    h = MyHTMLParser()
    h.feed(data=data, input=input)
    h.close()

    text = texttools.stripWhiteSpaces(h.getText())
#       print "title = %s" % h.getTitle()
#       text = htmltools.htmlToText(texttools.stripWhiteSpaces(h.getText())) or ""
#       text = texttools.stripWhiteSpaces(h.getText()) or ""
    if not h.getTitle():
        # we take the first 60 chars
        if len(text) < 60:
            title = text[0:60]
        else:
            end = 60
            while end > 0 and data[end] != ' ':
                end -= 1
                break
            title = text[0:end] + "..."
    else:
        title = h.getTitle()
#       return (htmltools.htmlToText(title), htmltools.htmlToText(text), h.getLinks())
    return (title, text, h.getLinks())
#       return (htmltools.htmlToText(texttools.stripWhiteSpaces(h.getTitle() or "")), htmltools.htmlToText(texttools.stripWhiteSpaces(h.getText() or "")))

#(title, text, links) = htmlToText(file('essai.html', 'r').read())
#print "title = %s" % title
#print "text = %s" % text
#print "links = %s" % links
