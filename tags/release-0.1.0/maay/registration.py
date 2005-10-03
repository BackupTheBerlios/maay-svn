"""this module defines the central registration server.

The Registration server keeps track of every connected
node.
"""

__revision__ = '$Id$'

import time

from twisted.protocols.basic import LineReceiver

class RegistrationServer(LineReceiver):

    def __init__(self):
        self._registeredUsers = {}
        
    def lineReceived(self, line):
        """received lines should match the following format :
        action:parm1:param2:...:paramn
        """
        try:
            action, param = line.split(':', 1)
        except ValueError:
            result = "unable to decode action: <%s>" % action
        else:
            callback = getattr(self, 'do_%s' % action, None)
            if callback:
                result = callback(param)
            else:
                result = "received invalid action: <%s>" % action
        
    def do_login(self, nodeId):
        print "%s accepts %s" % (id(self), nodeId)
        if nodeId in self._registeredUsers:
            print "%s was already registered" % (nodeId,)
        self._registeredUsers[nodeId] = time.time()

    def do_logout(self, nodeId):
        try:
            del self._registeredUsers[nodeId]
        except KeyError:
            print "%s was not registered" % (nodeId,)

    def do_who(self):
        """returns the list of logged in nodes"""
        for nodeId in self._registeredUsers:
            self.sendLine(nodeId)
    
