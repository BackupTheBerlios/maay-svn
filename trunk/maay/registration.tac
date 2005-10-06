#!/usr/bin/twistd2.3 -noy 
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


from twisted.application import service, internet
from twisted.internet.protocol import ServerFactory

from maay.registration import RegistrationServer

application = service.Application("registrationServer")
factory = ServerFactory()
factory.protocol = RegistrationServer
internet.TCPServer(2345, factory, interface='127.0.0.1').setServiceParent(application)
