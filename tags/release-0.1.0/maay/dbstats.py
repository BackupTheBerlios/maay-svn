#!/usr/bin/python
"""Helper script to display how many rows are stored in the various maay tables on localhost"""

from MySQLdb import connect

cnx = connect(user='maay', passwd='maay', use_unicode=True, db='maay')
cursor = cnx.cursor()
tables = ['document_providers', 'document_scores', 'documents',
          'files', 'node_interests', 'nodes', 'words']
for table  in tables:
    cursor.execute('select count(*) from %s'%table)
    nbRows = cursor.fetchone()[0]
    print "Table %s: %d rows" % (table, nbRows)

cnx.close()
    
