#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     General Public License for more details.
#
#     You should have received a copy of the GNU General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


from maay.configuration import NodeConfiguration, IndexerConfiguration

nodeConfig = NodeConfiguration()
nodeConfig.load()
indexerConfig = IndexerConfiguration()
indexerConfig.load_from_files()

NODE_PORT = nodeConfig.rpcserver_port
NODE_ID = nodeConfig.get_node_id()

QUERY_LIFE_TIME = nodeConfig.query_life_time
