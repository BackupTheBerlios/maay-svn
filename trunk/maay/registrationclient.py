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

from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator
from twisted.protocols.basic import LineReceiver
from time import mktime

class RegistrationClient(LineReceiver):
    def __init__(self, nodeRegistrationCallback):
        self.__callback = nodeRegistrationCallback
        
    def login(self, nodeId, ip, port, bandwidth) :
        print "login to registration server (node %s at %s:%s)" % (nodeId, ip, port)
        self.transport.write('login:%s:%s:%s:%s\r\n' % (nodeId, ip,
                                                     port, bandwidth))
        return self

    def logout(self, nodeId):
        print "logout from registration server (node %s)" % nodeId
        self.transport.write('logout:%s\r\n' % nodeId)
        self.transport.loseConnection()

    def who(self):
        print "querying registration server"
        self.transport.write('who:\r\n')

    def lineReceived(self, data):
        data = data.strip()
        print "registration server said", data
        if data.startswith('EOT'):
            self.transport.loseConnection()
            return
        time, nodeId, nodeIP, nodePort, nodeBandwidth = data.split('\t')
        lastSeenTime = parseTime(time)
        self.__callback(nodeId, nodeIP, nodePort, nodeBandwidth, lastSeenTime)
        

def parseTime(isodatetime):
    date, time = isodatetime.split('T')
    date = [int(s) for s in date.split('-')]
    time = [int(float(s)) for s in time.split(':')]
    return mktime(tuple(date+time+[0,0,0]))


def login(reactor, regIP, regPort, querier, nodeId, nodeIP, xmlrpcPort, bandwidth):
    if querier is not None:
        c = ClientCreator(reactor, RegistrationClient, querier.registerNode)
        d = c.connectTCP(regIP, regPort)
        d.addCallback(RegistrationClient.login, nodeId, nodeIP, xmlrpcPort, bandwidth)
        d.addCallback(RegistrationClient.who)
    else:
        print "Login : no querier found => no registration / no P2P"


def logout(reactor, regIp, regPort, nodeId):
    print "Registration@%s:%s (node %s) wants to log out." % (regIp, regPort, nodeId)
    c = ClientCreator(reactor, RegistrationClient, None)
    d = c.connectTCP(regIp, regPort)
    d.addCallback(RegistrationClient.logout)
