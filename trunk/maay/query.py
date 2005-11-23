#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

__revision__ = '$Id$'

def normalizeMimetype(fileExtension):
    import mimetypes
    return mimetypes.types_map.get('.%s' % fileExtension)

def parseWords(rawWords):
    """takes a (u)string
       returns a list of ustrings and dict of restrictions
    """
    assert(isinstance(rawWords, str) or isinstance(rawWords, unicode))
    rawWords = rawWords.split()
    words = []
    restrictions = {}
    for word in rawWords:
        try:
            restType, restValue = [s.strip() for s in word.split(':')]
        except ValueError:
            if isinstance(word, str):
                word = unicode(word, 'utf-8')
            words.append(word)
        else:
            if restType in Query.restrictions:
                # Python does not support unicode keywords !
                # (note: restType is pure ASCII, so no pb with str())
                restrictions[str(restType)] = restValue
            else:
                words.append(word)
    return words, restrictions

class Query(object):
    restrictions = ('filetype', 'filename', 'searchtype')
    
    def __init__(self, words, offset=0, filetype=None, filename=None,
                 order=None, direction=None):
        self.words = words # unicode string 
        self.offset = offset
        self.filetype = filetype
        self.filename = filename
        self.limit = None
        #FIXME: ugly stuff below, related to result
        #       presentation in the browser
        self.order = order or 'publication_time'
        self.direction = direction or 'DESC'

    def fromRawQuery(rawQuery, offset=0):
        """:type rawQuery: str"""
        _ , restrictions = parseWords(rawQuery)
        return Query(rawQuery, offset, **restrictions)
    fromRawQuery = staticmethod(fromRawQuery)

    def fromContext(context):
        """:type context: nevow's context objects"""
        wordsInContext  = context.arg('words') or ''
        rawQuery = unicode(wordsInContext, 'utf-8')
        offset = int(context.arg('offset', 0))
        return Query.fromRawQuery(rawQuery, offset)
    fromContext = staticmethod(fromContext)

    ###### Words accessors
    def getwords(self):
        return getattr(self, '_words', None)
    
    def setwords(self, words):
        self._words, _ = parseWords(words)

    words = property(getwords, setwords)

    def joinwords(self, join):
        return join.join(self._words)

    ###### Order & Direction accessors
    def getorder(self):
        return getattr(self, '_order', None)

    def setorder(self, order):
        assert(order in ('publication_time', 'relevance', 'popularity'))
        self._order = order

    order = property(getorder, setorder)

    def getdirection(self):
        return getattr(self, '_direction', None)

    def setdirection(self, direction):
        direction = direction.upper()
        assert(direction in ('ASC', 'DESC'))
        self._direction = direction

    direction = property(getdirection, setdirection)

    ###### Filetype accessors
    def getFiletype(self):
        return getattr(self, '_filetype', None)

    def setFiletype(self, filetype):
        # try to guess if filetype is already normalized or not
        if filetype:
            mimetype = normalizeMimetype(filetype)
            if mimetype:
                self._filetype = mimetype
            else:
                self._filetype = filetype
        else:
            self._filetype = None
    filetype = property(getFiletype, setFiletype)

    def __repr__(self):
        return 'Query Object (%s, %s, %s)' % (self.words, self.filetype,
                                              self.filename)

