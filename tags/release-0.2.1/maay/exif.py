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
    
