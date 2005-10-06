"""this module defines the central registration server.

The Registration server keeps track of every connected
node.
"""

__revision__ = '$Id$'

from datetime import datetime

from twisted.protocols.basic import LineReceiver

class RegistrationServer(LineReceiver):

    def __init__(self):
        # TODO: auto logout after a given time to save memory
        self._registeredUsers = {}
        
    def lineReceived(self, line):
        """received lines should match the following format :
        action:parm1:param2:...:paramn
        """
        try:
            action, param = line.split(':', 1)
        except ValueError:
            result = "unable to decode action: <%s>" % line
        else:
            callback = getattr(self, 'do_%s' % action, None)
            if callback:
                param = param.strip()
                if param:
                    args = param.split(':')
                    result = callback(*args)
                else:
                    result = callback()
            else:
                result = "received invalid action: <%s>" % action
        
    def do_login(self, nodeId, ip, port, bandwidth):
        print "%s accepts %s" % (id(self), nodeId)
        if nodeId in self._registeredUsers:
            print "%s was already registered" % (nodeId,)
        lastseen = datetime.utcnow().isoformat()
        self._registeredUsers[nodeId] = (lastseen,
                                         nodeId,
                                         ip,
                                         port,
                                         bandwidth)

    def do_logout(self, nodeId):
        try:
            del self._registeredUsers[nodeId]
        except KeyError:
            print "%s was not registered" % (nodeId,)

    def do_who(self):
        """returns the list of logged in nodes"""
        nodes = self._registeredUsers.values()
        nodes.sort()
        nodes.reverse()
        for nodeinfo in nodes:
            self.sendLine("\t".join(nodeinfo))
        self.sendLine('EOT')
