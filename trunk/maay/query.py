#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 2 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

__revision__ = '$Id$'

def normalizeMimetype(fileExtension):
    import mimetypes
    return mimetypes.types_map.get('.%s' % fileExtension)


class Query(object):
    restrictions = ('filetype', 'filename', 'searchtype')
    def __init__(self, words, offset=0, filetype=None, filename=None):
        self.words = words # unicode string 
        self.offset = offset
        self.filetype = normalizeMimetype(filetype)
        self.filename = filename

    def fromRawQuery(rawQuery, offset=0):
        """:type rawQuery: str"""
        rawWords = rawQuery.split()
        words = []
        restrictions = {}
        for word in rawWords:
            try:
                restType, restValue = [s.strip() for s in word.split(':')]
            except ValueError:
                words.append(word)
            else:
                if restType in Query.restrictions:
                    # Python does not support unicode keywords !
                    # (note: restType is pure ASCII, so no pb with str())
                    restrictions[str(restType)] = restValue
                else:
                    words.append(word)
        return Query(u' '.join(words), offset, **restrictions)
    fromRawQuery = staticmethod(fromRawQuery)

    def fromContext(context):
        """:type context: nevow's context objects"""
        rawQuery = unicode(context.arg('words'), 'utf-8')
        offset = int(context.arg('offset', 0))
        return Query.fromRawQuery(rawQuery, offset)
    fromContext = staticmethod(fromContext)

    def __repr__(self):
        return 'Query Object (%s, %s, %s)' % (self.words, self.filetype,
                                              self.filename)

