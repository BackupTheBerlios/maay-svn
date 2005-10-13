#!/usr/bin/python
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

"""Helper script to display how many rows are stored in the various maay tables on localhost"""

from MySQLdb import connect
from Scientific.Statistics.Histogram import Histogram

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

r = """SELECT count(word) from document_scores group by word"""
cursor.execute(r)
h = Histogram(cursor.fetchall(), 10)

for i in range(10):
    print h[i]



cnx.close()
    
