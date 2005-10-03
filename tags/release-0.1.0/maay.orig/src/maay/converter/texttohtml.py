import re

def __textToHTML(matchobj):
    if matchobj.group(0) == '<':
        return '&lt;'
    else:
        return '&gt;'

def textToHTML(text):
    # replace all special char by their equivalent in html
    # for the moment only < and > are replaced and may be enough
#       print "text = %s" % text
    return re.sub('<|>', __textToHTML, text)
