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
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import socket, os

def getUserLogin():
    """uses os.getlogin() when available, and if not provides a simple
    (and *unreliable*) replacement.
    """
    try:
        return os.getlogin()
    except (OSError, AttributeError):
        # OSError can occur on some Linux platforms.
        # AttributeError occurs on any non-UNIX platform
        # try to make a rough guess ...
        for var in ('USERNAME', 'USER', 'LOGNAME'):
            guessed = os.environ.get(var)
            if guessed:
                return guessed
        # could not guess username, use host name
        return socket.gethostname()



NODE_LOGIN = getUserLogin()
NODE_HOST = socket.gethostbyname(socket.gethostname())
