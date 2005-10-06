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


__revision__ = "$Id$"
from distutils.core import setup
import sys
from glob import glob

version = '0.1.0'
author = "France Telecom R&D and Logilab"
author_email = "maay-dev@lists.berlios.de"
copyright = "Copyright (c)2004-2005 France Telecom R&D"
description = "a network of peers for document search"
name = "Maay"
url = "http://maay.netofpeers.net/"
packages = ['maay']
data_files = [('maay/data', glob('maay/data/*')+glob('maay/data/images/*')),
                  ('maay/sql', glob('maay/sql/*.sql')),]
scripts = ['maay/bin/maay-server', 'maay/bin/maay-indexer']


class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        
maay_server = Target(description = "The maay server application",
			    icon_resources=[(1,  "maay/data/images/maay.ico"),],
			    script = 'maay/server.py',
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
                author_email = author_email,
		copyright = copyright,
		url = url
                )

else:
	setup(
		name = name,
		version = version,
		author = author,
                author_email = author_email,
		copyright = copyright,
		description = description,
		url = url,
		data_files = data_files,
		packages = packages,
                scripts = scripts
                )
