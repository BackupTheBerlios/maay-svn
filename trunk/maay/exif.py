"""This module provides tools for
   the exploitation of EXIF codes
   embedded in image files.
"""

#XXX: robustify this against missing PIL
try:
    import Image
except:
    print "Python Imaging Library not installed for your version of Python.",
    print "EXIF support will not work."
    
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
