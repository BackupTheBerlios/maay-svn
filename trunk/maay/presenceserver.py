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

"""this module defines the central presence server.

The Presence server keeps track of every connected
node.
"""

verbose = 1

__revision__ = '$Id$'

from datetime import datetime

from twisted.protocols.basic import LineReceiver

class PresenceServer(LineReceiver):
    # define this as a static class member since a new instance of the class
    # is created after each request
    _registeredUsers = {} 
    _ruTimestamp = {}
    # TODO: auto logout after a given time to save memory

    def __init__(self, autoExpirationDelayInSecs=3600*24):
        self._autoExpirationDelayInSecs = autoExpirationDelayInSecs

    def _auto_logout_everybody(self):
        """evicts registered nodes after some time
        """
        now = datetime.utcnow()
        for nodeId, values in PresenceServer._ruTimestamp.items():
            dt = now - values
            if dt.seconds > self._autoExpirationDelayInSecs:
                if verbose:
                    print "%s removed" % str(PresenceServer._registeredUsers[nodeId])
                del PresenceServer._registeredUsers[nodeId]
                del PresenceServer._ruTimestamp[nodeId]
            elif verbose:
                print "keep: %s (%s)" % (str(PresenceServer._registeredUsers[nodeId]), str(values))
        
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
        self._auto_logout_everybody()
        
    def do_notify(self, nodeId, ip, port, bandwidth):
        # For the moment, take IP and port from the TCP socket and not
        # those given by the client.
        # (to prevent client to give private address...)
        # TODO:
        # - if the server detect that the IP given by the client is a
        # private IP address, use those from the TCP socket
        # - the presence server tries to connect to the client to test
        # the information...
        if verbose:
           print "Notification from %s:%s (id:%s)" % (ip, port, nodeId)
        if nodeId in PresenceServer._registeredUsers:
            print "%s was already registered" % (nodeId,)
        lastseen = datetime.utcnow()
        PresenceServer._ruTimestamp[nodeId] = lastseen
        PresenceServer._registeredUsers[nodeId] = (lastseen.isoformat(),
                                         nodeId,
                                         ip,
                                         port,
                                         bandwidth)

    def do_logout(self, nodeId):
        try:
            print "%s logout" % str(PresenceServer._registeredUsers[nodeId])
            del PresenceServer._registeredUsers[nodeId]
            del PresenceServer._ruTimestamp[nodeId]
        except KeyError:
            print "%s was not registered" % (nodeId,)

    def do_who(self):
        """returns the list of logged in nodes"""
        nodes = PresenceServer._registeredUsers.values()
        nodes.sort()
        nodes.reverse()
        for nodeinfo in nodes:
            self.sendLine("\t".join(nodeinfo))
            print "list: %s" % str(nodeinfo)
        self.sendLine('EOT')
        print 'EOT'
