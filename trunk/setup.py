
__revision__ = "$Id$"
from distutils.core import setup
import sys
from glob import glob

version = '0.1.0'
author = "France Telecom R&D and Logilab"
copyright = "Copyright (c)2005 France Telecom R&D and Logilab"
description = "a network of peers for document search"
name = "Maay"
url = "http://maay.netofpeers.net/"
packages = ['maay']
data_files = [('maay/data', glob('maay/data/*')+glob('maay/data/images/*')),
                  ('maay/sql', glob('maay/sql/*.sql')),]


class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        
maay_server = Target(description = "The maay server application",
			    icon_resources=[(1,  "maay/data/images/maay.ico"),],
			    script = 'maay/main.py',
                            includes = ["MySQLdb"],
			    dest_base = "maay_server")
maay_indexer = Target(description = "The maay indexer application (CLI)",
			    icon_resources=[(1,  "maay/data/images/maay.ico"),],
			    script = 'maay/indexer.py',
			    dest_base = "maay_indexer")
createdb = Target(description = "Database creation utility",
			    script = 'maay/createdb.py',
			    dest_base = "createdb")


if sys.platform == 'win32':
	import py2exe
        if len(sys.argv) == 1:
            sys.argv.append('py2exe')
            
        
	setup(console = [maay_server, maay_indexer,createdb],
		name = name,
		version = version,
		description = description,
		author = author,
		copyright = copyright,
		url = url
                )

else:
	setup(
		name = name,
		version = version,
		author = author,
		copyright = copyright,
		description = description,
		url = url,
		data_files = data_files,
		packages = packages
                )