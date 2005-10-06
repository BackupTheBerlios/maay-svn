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

from twisted.internet.protocol import Protocol
from time import mktime

class RegistrationClient(Protocol):
    def __init__(self, nodeRegisterCallback):
        self._callback = nodeRegisterCallback
    def login(self, nodeId, ip, port, bandwidth):
        self.transport.write('login:%s:%d:%d\r\n' % (nodeId, ip, port, bandwidth))
        self.disconnect()

    def disconnect(self):
        self.transport.looseConnection()

    def logout(self, nodeId):
        self.transport.write('logout:%s\r\n' % nodeId)
        self.diconnect()

    def who(self):
        self.transport.write('who:\r\n')

    def lineReceived(self, data):
        data = data.strip()
        if data.startswith('EOT'):
            self.disconnect()
            return
        time, nodeId, nodeIP, nodePort, nodeBandwidth = data.split('\t')
        lastSeenTime = parseTime(time)
        self._callback(nodeId, nodeIP, nodePort, nodeBandwidth, lastSeenTime)
        

def parseTime(isodatetime):
    date, time = isodatetime.split('T')
    date = [int(s) for s in date.split('-')]
    time = [int(float(s)) for s in time.split(':')]
    return mktime(tuple(date+time+[0,0,0]))
