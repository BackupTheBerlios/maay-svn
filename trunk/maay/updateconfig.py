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

""" helper to create the indexer.ini configuration file at install time on windows"""
import os
import sys

config = """[INDEXER]
# Host on which the maay node is running
host=localhost
#Port on which the maay node is listening
port=6789

# User login on the maay node 
user=maay
# User password on the maay node
password=maay

# Which directories are to be indexed
#  - private indexed directories are not available to  queries from other nodes
#  - public indexed directories are available to these queries
#  - skip dirs are not indexed
#
# If a document is available through both a public and a private directory, 
# the public version prevails
#
# You can use a comma separated list of values to specify several
# directories in each configuration variable. 
private-index-dir=%(private)s
private-skip-dir=%(private_skip)s
public-index-dir=%(public)s
public-skip-dir=%(public_skip)s
"""

def createConfigFile(myDesktop, myDocuments):
    f=open("indexer.ini", "w")
    values = {'private'     : '%s,%s' % (myDesktop, myDocuments),
              'private_skip': '',
              'public'      : '%s\\Maay Documents' % myDesktop,
              'public_skip' : '',
              }
    f.write(config % values)
    f.close()
    
if __name__ == '__main__':
    createConfigFile(sys.argv[1], sys.argv[2])
	
