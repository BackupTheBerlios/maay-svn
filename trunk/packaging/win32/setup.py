# based on advanced sample in py2exe documentation

from distutils.core import setup
import py2exe
import sys

# If run without args, build executables, in quiet mode.
if len(sys.argv) == 1:
    sys.argv.append("py2exe")
    sys.argv.append("-q")

class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.version = "0.1.0"
        self.company_name = "Logilab"
        self.copyright = "copyright 2005 Logilab"
        self.name = "Maay"

maay_console = Target(
    # used for the versioninfo resource
    description = "A sample GUI app with console",

    # what to build
    script = "maay.py",
#    other_resources = [(RT_MANIFEST, 1, manifest_template % dict(prog="test_wx"))],
    dest_base = "maay_console")

setup(console = [maay_console])
