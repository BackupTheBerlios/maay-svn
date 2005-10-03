import maay.constants
import time
import globalvars
import re
import converter.texttohtml
import urllib

def get_excerpt(text, pos, excerpt_half_size=maay.constants.EXCERPT_HALF_SIZE, dot=False):
    if pos >= maay.constants.MAX_TEXT_CONTENT_STORED_SIZE:
        pos = 0
    start = max(0, pos - excerpt_half_size)
    if start > 0:
        while start < pos and text[start] != ' ':
            start += 1
        start += 1

    end = min(len(text), start + excerpt_half_size * 2)

    if end < len(text):
        while end > pos and text[end] != ' ':
            end -= 1

    r = text[start:end + 1]
    if dot:
        if start > 0:
            r = "...%s" % r
        if end < len(text):
            r = "%s..." % r
    return r

def putInBold(str, words):
    if not str:
        return ""
    for word in words:
#               pattern = "(^| |,|;|!|\?|<|>|\.)(" + word + ")($| |,|;|!|\?|<|>|\.)"
#               pattern = "(^|\W+)(%s)($|\W+)" % globalvars.accent.extendsMatchingPattern(word)
        pattern = "(%s)" % globalvars.accent.extendsMatchingPattern(word)

        p = re.compile(pattern)
        str = p.sub("<b>\g<1></b>", str)

    return str


def mergeExcerpts(documentInfo, ds, words, excerpt_half_size = maay.constants.EXCERPT_HALF_SIZE):
    documentScores = []
    for d in ds:
        if d.word in words:
            documentScores.append(d)

    documentScores.sort(lambda x, y: int(x.position - y.position))

    str = ""
    lastEndPosition = 0

    for documentScore in documentScores:
        excerpt = get_excerpt(documentInfo.text, documentScore.position, excerpt_half_size=excerpt_half_size)
#               excerpt = documentScore.excerpt
        if not excerpt or excerpt == "":
            continue

        # todo: check for accented text
        m = re.search("(^|\W+)(%s)(\W+|$|:)" % documentScore.word, excerpt, re.IGNORECASE)

        if not m or documentScore.position == -1:
            str += excerpt
            endPosition = len(excerpt)
        else:
            pos = m.start()

            startPosition = documentScore.position - pos
            endPosition = len(excerpt) - pos + documentScore.position

            if startPosition <= lastEndPosition:
                str += converter.texttohtml.textToHTML(excerpt[pos - (documentScore.position - lastEndPosition):])
            else:
                if documentScore.position - excerpt_half_size > 0:
                    str += "<b>...</b>"
                str += converter.texttohtml.textToHTML(excerpt)

        lastEndPosition = endPosition

    if not str:
        return None

    str += " <b>...</b>"
    return str

def size_str(s):
    if s < 1024:
        return "%d bytes" % s
    elif s < 1048576:
        return "%.1f k" % (float(s) / 1024)
    else:
        return "%.1f M" % (float(s) / 1048576)

def date_str(t):
    return time.strftime("%d %b %Y", time.localtime(t))

def long_date_str(t):
    return time.strftime("%d %b %Y %H:%M:%S", time.localtime(t))

def quote_url(url):
    return urllib.quote(url)

#
# COLORS
#
PUBLISHED_DOCUMENT_COLOR = '#00ff00'
CACHED_DOCUMENT_COLOR = '#ffff00'
PRIVATE_DOCUMENT_COLOR = '#0000ff'
KNOWN_DOCUMENT_COLOR = '#ff0000'
UNKNOWN_DOCUMENT_COLOR = '#000000'
INTERNET_DOCUMENT_COLOR = '#aa8844'
INTRANET_DOCUMENT_COLOR = '#44ff44'

DESKTOP_SEARCH_COLOR = '#448844'
DESKTOP_SEARCH_LIGHT_COLOR = '#ccffcc'

MAAY_SEARCH_COLOR = '#884444'
MAAY_SEARCH_LIGHT_COLOR = '#ffcccc'

INTERNET_SEARCH_COLOR = '#4444aa'
INTERNET_SEARCH_LIGHT_COLOR = '#ccccff'

INTRANET_SEARCH_COLOR = '#888844'
INTRANET_SEARCH_LIGHT_COLOR = '#ffffcc'

def getDocumentStateColor(state):
    if state == maay.datastructure.documentinfo.PUBLISHED_STATE:
        return PUBLISHED_DOCUMENT_COLOR
    elif state == maay.datastructure.documentinfo.KNOWN_STATE:
        return KNOWN_DOCUMENT_COLOR
    elif state == maay.datastructure.documentinfo.CACHED_STATE:
        return CACHED_DOCUMENT_COLOR
    elif state == maay.datastructure.documentinfo.PRIVATE_STATE:
        return PRIVATE_DOCUMENT_COLOR
    elif state == maay.datastructure.documentinfo.UNKNOWN_STATE:
        return UNKNOWN_DOCUMENT_COLOR

def getSearchRangeColor(search_range):
    if search_range == maay.constants.DESKTOP_SEARCH_RANGE:
        return DESKTOP_SEARCH_COLOR
    elif search_range == maay.constants.MAAY_SEARCH_RANGE:
        return MAAY_SEARCH_COLOR
    elif search_range == maay.constants.INTRANET_SEARCH_RANGE:
        return INTRANET_SEARCH_COLOR
    elif search_range == maay.constants.INTERNET_SEARCH_RANGE:
        return INTERNET_SEARCH_COLOR


def getSearchRangeLightColor(search_range):
    if search_range == maay.constants.DESKTOP_SEARCH_RANGE:
        return DESKTOP_SEARCH_LIGHT_COLOR
    elif search_range == maay.constants.MAAY_SEARCH_RANGE:
        return MAAY_SEARCH_LIGHT_COLOR
    elif search_range == maay.constants.INTRANET_SEARCH_RANGE:
        return INTRANET_SEARCH_LIGHT_COLOR
    elif search_range == maay.constants.INTERNET_SEARCH_RANGE:
        return INTERNET_SEARCH_LIGHT_COLOR

def getSearchRangeName(search_range):
    if search_range == maay.constants.DESKTOP_SEARCH_RANGE:
        search_range_name = "Recherche locale"
    elif search_range == maay.constants.MAAY_SEARCH_RANGE:
        search_range_name = "Recherche dans le réseau Maay"
    elif search_range == maay.constants.INTRANET_SEARCH_RANGE:
        search_range_name = "Recherche dans l'intranet"
    elif search_range == maay.constants.INTERNET_SEARCH_RANGE:
        search_range_name = "Recherche dans l'Internet"
    return search_range_name
