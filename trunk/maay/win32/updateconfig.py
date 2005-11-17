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

""" helper to create the indexer.ini configuration file at install time on windows"""

__revision__ = '$Id$'
import os
import sys

indexer_config = """[INDEXER]
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

node_config = """[NODE]
db-name=maay
db-host=localhost
user=maay
password=maay
presence-host=%(presence)s
presence-port=%(port)d
download-index-dir=%(download)s
"""
import socket

def createConfigFile(myDesktop, myDocuments):
    f=open("indexer.ini", "w")
    values = {'private'     : '%s,%s' % (myDesktop, myDocuments),
              'private_skip': '',
              'public'      : '%s\\Maay Documents' % myDesktop,
              'public_skip' : '',
              }
    f.write(indexer_config % values)
    f.close()

    f = open("node.ini", "w")
    presence, port = probe_presence_config()
    values = {'presence': presence,
              'port': port,
              'download': '%s\\Maay Documents\\downloaded' % myDesktop,}
    f.write(node_config % values)
    f.close()

def probe_presence_config():
    default = ('192.33.178.29', 2345)
    private_ft = ('10.193.165.35', 2345)
    crater = ('172.17.1.4', 2345)
    jenkins = ('192.168.74.105', 2345)
    for addr in (private_ft,
                 default, # public FT server
                 crater,    # private logilab server
                 jenkins,# private logilab server
                 ):
        print 'probing', addr
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(addr)
            s.close()
        except socket.error, exc:
            continue
        else:
            print "found presence server listening at %s:%d" % addr
            return addr
    print "using default configuration: %s:%d" % default
    return default
        
    
if __name__ == '__main__':
    createConfigFile(sys.argv[1], sys.argv[2])
	
