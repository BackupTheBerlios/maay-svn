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

""" helper to create the maay mysql instance on windows platform"""

__revision__ = '$Id$'

import os

def do_delete():
    pipe = os.popen(r'mysql\bin\mysql.exe -u root mysql', 'w')
    pipe.write('DROP DATABASE maay;\n')
    pipe.close()
    

def do_create():
    pipe = os.popen(r'mysql\bin\mysql.exe -u root mysql', 'w')
    data = file('mysql.sql','rb').read()
    pipe.write(data)
    pipe.close()
    
if __name__ == '__main__':
    do_delete()
    do_create()
	
	
