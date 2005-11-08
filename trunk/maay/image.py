"""Some utilities to manipulate images"""

try:
    import Image
except:
    print "Python Imaging Library not installed for your version of Python.",
    print "Thumbnail support will not work."

from tempfile import mkdtemp
import stat, os, os.path as osp
from maay.exif import *
from maay.configuration import Configuration

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

class NoThumbnailsDir(Exception):
    """Represents impossibility to access or create RW the
       maay thumbnails dir repository"""
    pass
        
class ImageConfiguration(Configuration):
    options = Configuration.options + [
        ('thumbnails-dir',
         {'type' : "string", 'metavar' : "--thumbnailsdir", 'short' : "-thumbs",
          'help' : "Thumbnail files repository",
          'default' : '.maay_thumbnails'},)]
    config_file = 'image.ini'

    def __init__(self):
        Configuration.__init__(self, name="Image")

    def get_thumbnails_dir(self):
        """Returns the complete path to Maay thumnails directory
           XXX: It will try to create the dir if absent"""
        path = osp.join(osp.expanduser('~'),
                        self.get('thumbnails-dir'))
        if not os.access(path, os.W_OK):
            try:
                os.makedirs(path, stat.S_IRWXU)
            except Exception, e:
                raise NoThumbnailsDir("Impossible to access or create %s. "
                                      "Cause : %e" % (path, e))
        if os.access(path, os.W_OK): # yes, I'm paranoId
            return path
        else:
            raise NoThumbnailsDir("Access to %s is impossible." % path)

    
            
