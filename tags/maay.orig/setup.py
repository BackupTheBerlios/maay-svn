"""
Top-level builder

"""

import os
import sys
import distutils.core
import glob

# TODO: installation for Mac OS X (package py2app)
# TODO: package generation for Linux (rpm & deb)

name="Maay"
version="0.2"
description="Maay, the all-in-one search engine"
author="Frederic DANG NGOC"
author_email="frederic.dangngoc@rd.francetelecom.com"
url="http://maay.rd.francetelecom.fr"

class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.version = version
        self.company_name = "France Telecom R&D"
        self.copyright = "no copyright"
        self.name = "Maay executable"
        self.url = url

################################################################
# a NT service, modules is required

#dir = os.path.join(os.path.dirname(sys.argv[0]), "src")
#os.chdir(dir)
#os.environ["PYTHONPATH"] = os.path.join(os.path.dirname(sys.argv[0]), "external\\windows")
sys.path.append("src")

archpath="arch/%s" % os.name

data_files = [
	("", glob.glob("*.ico")),
	("config", glob.glob("config/*.*") + glob.glob("%s/conf/*.*" % archpath)),
	("config/languages", glob.glob("config/languages/*.*")),
	("config/templates", glob.glob("config/templates/*.*")),
	("config/templates/includes", glob.glob("config/templates/includes/*.*")),
	("docs", glob.glob("docs/*.*")),
	("logs", []),
	("www/cache", []),
	("www/htdocs", glob.glob("www/htdocs/*.*")),
	("www/htdocs/css", glob.glob("www/htdocs/css/*.*")),
	("www/htdocs/images", glob.glob("www/htdocs/images/*.*")),
	("www/pub", []),
	("www/tmp", [])
		]

if os.name == 'nt':
	import py2exe

	includes = ["encodings",
        	    "encodings.latin_1",]

	maayservice = Target(
		description = "Maay service",
		modules = "win32maayservice",
		script = "src/win32maayservice.py",
		icon_resources=[(1, "maay.ico")]
	)

	maaymain = Target(
	    description = "Maay Main",
	    modules = "maay.maaymain",
	    script = "src/maay/maaymain.py",
	    icon_resources=[(1, "maay.ico")]
	    )
    
	maaysearch = Target(
	    description = "Maay",
	    modules = "win32maayrun",
	    script = "src/win32maayrun.py",
	    dest_base = "win32maayrun",
	    icon_resources=[(1, "maay.ico")]
	    )

	data_files.extend([
		("external/windows", ["external\\windows\\start.bat"]),
		("external/windows/antiword", glob.glob("external\\windows\\antiword\\*.*")),
		("external/windows/xpdf", glob.glob("external\\windows\\xpdf\\*.*")),
		("external/windows/mysql", glob.glob("external\\windows\\mysql\\*.*")),
		("external/windows/mysql/bin", glob.glob("external\\windows\\mysql\\bin\\*.*")),
		("external/windows/mysql/data/mysql", glob.glob("external\\windows\\mysql\\data\\mysql\\*.*")),
		("external/windows/mysql/data/test", glob.glob("external\\windows\\mysql\\data\\test\\*.*")),
		("external/windows/mysql/share/french", glob.glob("external\\windows\\mysql\\share\\french\\*.*")),
		("external/windows/mysql/share/english", glob.glob("external\\windows\\mysql\\share\\english\\*.*"))
	])

	distutils.core.setup(
		name=name,
		version=version,
		description=description,
		author=author,
		author_email=author_email,
		url=url,
		options={"py2exe":{"optimize":2, "packages": ["encodings"]}},
		service=[maayservice],
		console = [maaysearch, maaymain], 
		data_files=data_files)
else:
	print "---------------------"
	print "dir = %s" % os.getcwd()
	print "prefix = %s" % sys.prefix
	print "sys.argv = %s" % sys.argv
	print "---------------------"
	#os.chdir(os.path.dirname(sys.argv[0]))
	distutils.core.setup(
		name=name,
		version=version,
		description=description,
		author=author,
		author_email=author_email,
		url=url,
# 		package_dir={"": "src"},
		packages=['maay', 'maay/converter', 'maay/config', 'maay/datastructure', 'maay/linux', 'maay/win32'],
		data_files=data_files,
	)

#

