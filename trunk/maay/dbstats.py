#!/usr/bin/python

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

"""Helper script to display how many rows are stored in the various
maay tables on localhost"""

__revision__ = '$Id$'

from MySQLdb import connect
from pylab import hist, show

cnx = connect(user='maay', passwd='maay', use_unicode=True, db='maay')
cursor = cnx.cursor()
tables = ['document_providers', 'document_scores', 'documents',
          'files', 'node_interests', 'nodes', 'words']

size = {}
for table  in tables:
    cursor.execute('select count(*) from %s'%table)
    nbRows = cursor.fetchone()[0]
    size[table] = nbRows
    print "Table %s: %d rows" % (table, nbRows)

r = """SELECT count(word) FROM document_scores GROUP BY word LIMIT 10000"""
cursor.execute(r)
data = [int(e[0]) for e in cursor.fetchall() if int(e[0])!=1]
print data
h = hist(data, 1000)
show()

cnx.close()
    
