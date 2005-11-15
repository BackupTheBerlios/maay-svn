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

"""Utility script to clean the database. This forces full reindexation
on the following indexer run
"""
__revision__ = '$Id$'

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
