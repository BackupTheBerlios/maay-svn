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
    """Client-side stuff to ask/request things from the registration server.
       Tightly coupled with registration.py
    """
    
    def __init__(self, nodeRegistrationCallback):
        self._callback = nodeRegistrationCallback
        self._lineCount = 0
        
    def login(self, nodeId, ip, port, bandwidth) :
        print "RegistrationClient login to registration server (node %s at %s:%s)" \
              % (nodeId, ip, port)
        self.transport.write('login:%s:%s:%s:%s\r\n' \
                             % (nodeId, ip, port, bandwidth))
        return self

    def logout(self, nodeId):
        print "RegistrationClient logout from registration server (node %s)" % nodeId
        self.transport.write('logout:%s\r\n' % nodeId)
        self.transport.loseConnection()

    def who(self):
        print "RegistrationClient who"
        self.transport.write('who:\r\n')

    def lineReceived(self, data):
        """receiving end of the client
           for each method of RegisterClient, we might get
           an int (=len(registered nodes)) number of lines,
           to be properly transformed back
           to complete node identification data
           WE are responsible for the correct unpacking of said data here
           """
        self._lineCount += 1
        data = data.strip()
        print "RegistrationClient lineReceived (%s) said %s" % (self._lineCount, data)
        if data.startswith('EOT'):
            self.transport.loseConnection()
            return
        time, nodeId, nodeIP, nodePort, nodeBandwidth = data.split('\t')
        lastSeenTime = parseTime(time)
        self._callback(nodeId, nodeIP, nodePort, nodeBandwidth, lastSeenTime)
        

def parseTime(isodatetime):
    date, time = isodatetime.split('T')
    date = [int(s) for s in date.split('-')]
    time = [int(float(s)) for s in time.split(':')]
    return mktime(tuple(date+time+[0,0,0]))


def login(reactor, regIP, regPort, querier, nodeId, nodeIP, xmlrpcPort, bandwidth):
    """registers and transmits the node catalog to querier.registerNode
    """
    if querier is not None:
        c = ClientCreator(reactor, RegistrationClient, querier.registerNode)
        d = c.connectTCP(regIP, regPort)
        d.addCallback(RegistrationClient.login, nodeId, nodeIP, xmlrpcPort, bandwidth)
        d.addCallback(RegistrationClient.who)
    else:
        print "Login : no querier found => no registration / no P2P"

def askWho(reactor, regIp, regPort, callback):
    """transmits node catalog to the callback"""
    c = ClientCreator(reactor, RegistrationClient, callback)
    d = c.connectTCP(regIp, regPort)
    d.addCallback(RegistrationClient.who)

def logout(reactor, regIp, regPort, nodeId):
    print "Registrator@%s:%s node %s wants to log out." % (regIp, regPort, nodeId)
    c = ClientCreator(reactor, RegistrationClient, None)
    d = c.connectTCP(regIp, regPort)
    d.addCallback(RegistrationClient.logout)
