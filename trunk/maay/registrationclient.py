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
