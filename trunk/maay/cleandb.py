#!/usr/bin/python
"""Utility script to clean the database. This forces full reindexation
on the following indexer run
"""

from maay.indexer import IndexerConfiguration
from logilab.common.db import get_dbapi_compliant_module

config = IndexerConfiguration()
config.load()


dbapiMod = get_dbapi_compliant_module('mysql')
connection = dbapiMod.connect(host=config.host, database='maay',
                              user=config.user, password=config.password,
                              unicode=True)

cursor = connection.cursor()
for table in ('nodes', 'document_providers', 'documents', 'document_scores', 'words', 'files', 'node_interests'):
    nrows = cursor.execute('DELETE FROM %s;' % table)
    print "Deleted %d rows from table %s" % (nrows, table)
connection.commit()
