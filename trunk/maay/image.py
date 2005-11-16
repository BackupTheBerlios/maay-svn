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

"""Some utilities to manipulate images"""

__revision__ = '$Id$'

import stat, os, os.path as osp
import sys

import Image

############# Thumbnail bizness

class ThumbnailCreationError(Exception):
    """Signals impossibility to create a thumbnail"""
    pass

def make_thumbnail(file_path, target_dir, size=128):
    """Creates a thumbnail and returns the associated file path"""
    try:
        im = Image.open(file_path)
        thumb_size = (size, size)
        im.thumbnail(thumb_size)
        target_file = osp.join (target_dir, 'thumb-' + osp.basename(file_path))
        im.save(target_file, 'JPEG')
        return unicode(target_file)
    except Exception, e:
        raise ThumbnailCreationError("Cause : %e" % e)


############## EXIF stuff
from maay.configuration import ImageConfiguration as ImConfig
from maay.texttool import AbstractParser

class ExifParser(AbstractParser):
    """A parser for Exif information found in image files"""

    def __init__(self):
        self.thumbnails_dir = None

    def get_thumbnails_dir(self):
        if not self.thumbnails_dir:
            self.thumbnails_dir = ImConfig().get_thumbnails_dir()
        return self.thumbnails_dir

    def parseFile(self, filepath, pristineFilename, encoding=None):
        """returns a 4-uple (title, normalized_text, links, offset)
        TODO: port original code from htmltotext
        :param encoding: if None, then need to be guessed
        """
        title = unicode(pristineFilename, sys.getfilesystemencoding())
        try:
            result = 'EXIF : ' + get_ustring_from_exif(filepath)
##             try:
##                 thumb = make_thumbnail(filepath, self.get_thumbnails_dir())
##             except Exception, e:
##                 print "Can't make thumbnail. Cause : %s" % e
##                 traceback.print_exc()
##                 thumb = None
##             return title, result, [thumb], 0
            return title, result, [], 0
        except Exception, e:
            print "No EXIF nor thumbnails. Cause : %s" % e
        return title, u'No EXIF information available', [], 0

# Mapping from number to (descriptor, type)
exif_dict = {
    256 : ('ImageWidth', int),
    257 : ('ImageLength', int),
    258 : ('BitPerSample', int),
    259 : ('Compression', int),
    270 : ('ImageDescription', str),
    271 : ('Make', str),
    272 : ('Model', str),
    274 : ('Orientation', int),
    305 : ('Software', str),
    306 : ('DateTime', str),
    315 : ('Artist', str),


    33434 : ('ExposureTime', (int, int)),

    36864 : ('ExifVersion', None),
    37122 : ('CompressedBitsPerPixel', (int, int)),

#    37500 : ('MakerNote', None), too much garbage there

    36867 : ('DateTimeOriginal', str),
    36868 : ('DateTimeDigitized', str),

    40962 : ('PixelXDimension', int),
    40963 : ('PixelYDimension', int),
    
    }

def raw_get_exif(file_path):
    """gets a mapping from exif codes to values"""
    return Image.open(file_path)._getexif()

def get_exif(file_path):
    """returns a mapping from exif attributes to values"""
    res = {}
    for k, v in raw_get_exif(file_path).items():
        if exif_dict.has_key(k):
            res[exif_dict[k][0]] = v
    return res

def get_string_from_exif(filepath):
    """returns a well formed string from
       exif attributes to values"""
    d = get_exif(filepath)
    res = ''
    for k, v in d.items():
        res += k+' : '+str(v)+'\n'
    return res

def get_ustring_from_exif(filepath):
    """returns a well formed unicode string from
       exif attributes to values"""
    d = get_exif(filepath)
    res = u''
    for k, v in d.items():
        res += unicode(k)+u' : '+unicode(v)+u'\n'
    return res


    
            
