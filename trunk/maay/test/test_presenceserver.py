#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This program is free software; you can redistribute it and/or modify it
#     under the terms of the GNU General Public License as published by the
#     Free Software Foundation; either version 2 of the License, or (at your
#     option) any later version.
#     
#     This program is distributed in the hope that it will be useful, but
#     WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
#     Public License for more details.
#     
#     You should have received a copy of the GNU General Public License along
#     with this program; if not, write to the Free Software Foundation, Inc.,
#     59 Temple Place - Suite 330, Boston, MA 02111-1307 USA.
#     

"""unit tests for presenceserver.py
"""
__revision__ = '$Id: test_boilerplate.py 481 2005-11-15 08:10:46Z afayolle $'

import unittest
from maay.presenceserver import PresenceServer

class MockTransport:

    def __init__(self, host):
        self.host = host

    def getPeer(self):
        return self


class MockLineReceiver:

    def __init__(self):
        self.lines = []
    
    def sendLine(self, line):
        elts = line.split()
        if len(elts) > 1:
            self.lines.append(elts[1:])
        else:
            self.lines.append(elts)


class PresenceServerTC(unittest.TestCase):
    """test suite to be completed ...
    """
    def setUp(self):
        self.srv = PresenceServer()
        
    def tearDown(self):
        PresenceServer._registeredUsers = {}
        PresenceServer._ruReverseMap = {}
        PresenceServer._ruTimestamp = {}
        
    def testSimpleNotify(self):
        self.srv.transport = MockTransport('1.2.3.4')
        self.assertEquals(self.srv._registeredUsers, {})
        self.assertEquals(self.srv._ruReverseMap, {})
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        # check first injection
        self.assertEquals(self.srv._registeredUsers['FOONODEA'][1:],
                          ('FOONODEA','1.2.3.4','5678','9'))
        self.assertEquals(self.srv._ruReverseMap[('1.2.3.4','5678')],
                          'FOONODEA')
        # inject second
        self.srv.lineReceived("notify:FOONODEB:1.2.3.4:567:8")        
        # check both are still there
        self.assertEquals(self.srv._registeredUsers['FOONODEA'][1:],
                          ('FOONODEA','1.2.3.4','5678','9'))
        self.assertEquals(self.srv._registeredUsers['FOONODEB'][1:],
                          ('FOONODEB','1.2.3.4','567','8'))
        self.assertEquals(self.srv._ruReverseMap,
                          {('1.2.3.4', '5678') : 'FOONODEA',
                           ('1.2.3.4', '567') : 'FOONODEB',})


##     def testNotifyTwice(self):
##         self.srv.transport = MockTransport('1.2.3.4')
##         self.assertEquals(self.srv._registeredUsers, {})
##         self.assertEquals(self.srv._ruReverseMap, {})
##         self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
##         self.srv.lineReceived("notify:FOONODEB:1.2.3.4:5678:9")
##         self.assertEquals(self.srv._registeredUsers['FOONODEB'][1:],
##                           ('FOONODEB','1.2.3.4','5678','9'))
##         self.assertEquals(self.srv._ruReverseMap[('1.2.3.4','5678')],
##                           'FOONODEB')


    def testWho(self):
        self.srv.transport = MockTransport('1.2.3.4')
        mockLineReceiver = MockLineReceiver()
        self.srv.sendLine = mockLineReceiver.sendLine
        self.assertEquals(self.srv._registeredUsers, {})
        self.assertEquals(self.srv._ruReverseMap, {})
        # who ?
        self.srv.do_who()
        self.assertEquals(mockLineReceiver.lines, [['EOT']])
        mockLineReceiver.lines = []
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        self.srv.lineReceived("notify:FOONODEB:1.2.3.4:567:8")
        self.assertEquals(self.srv._registeredUsers['FOONODEA'][1:],
                          ('FOONODEA','1.2.3.4','5678','9'))
        self.assertEquals(self.srv._registeredUsers['FOONODEB'][1:],
                          ('FOONODEB','1.2.3.4','567','8'))
        self.assertEquals(self.srv._ruReverseMap,
                          {('1.2.3.4', '5678') : 'FOONODEA',
                           ('1.2.3.4', '567') : 'FOONODEB',})
        # who again
        self.srv.do_who()
        self.assertEquals(mockLineReceiver.lines,
                          [['FOONODEB','1.2.3.4','567','8'],
                           ['FOONODEA','1.2.3.4','5678','9'],
                           ['EOT']])

    def testLogout(self):
        self.srv.transport = MockTransport('1.2.3.4')
        mockLineReceiver = MockLineReceiver()
        self.srv.sendLine = mockLineReceiver.sendLine
        self.assertEquals(self.srv._registeredUsers, {})
        self.assertEquals(self.srv._ruReverseMap, {})
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        self.srv.lineReceived("notify:FOONODEB:1.2.3.4:567:8")
        self.assertEquals(self.srv._registeredUsers['FOONODEA'][1:],
                          ('FOONODEA','1.2.3.4','5678','9'))
        self.assertEquals(self.srv._registeredUsers['FOONODEB'][1:],
                          ('FOONODEB','1.2.3.4','567','8'))
        self.assertEquals(self.srv._ruReverseMap,
                          {('1.2.3.4', '5678') : 'FOONODEA',
                           ('1.2.3.4', '567') : 'FOONODEB',})
        # real test begin there
        self.srv.do_logout('FOONODEA')
        self.assertRaises(KeyError,
                          self.srv._registeredUsers.__getitem__,
                          'FOONODEA')
        self.assertEquals(self.srv._registeredUsers['FOONODEB'][1:],
                          ('FOONODEB','1.2.3.4','567','8'))
        self.assertEquals(self.srv._ruReverseMap,
                          {('1.2.3.4', '567') : 'FOONODEB',})
       
    def testAutoLogout(self):
        PresenceServer._autoExpirationDelayInSecs = .1
        self.srv.transport = MockTransport('1.2.3.4')
        mockLineReceiver = MockLineReceiver()
        self.srv.sendLine = mockLineReceiver.sendLine
        self.assertEquals(self.srv._registeredUsers, {})
        self.assertEquals(self.srv._ruReverseMap, {})
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        self.srv.lineReceived("notify:FOONODEB:1.2.3.4:567:8")
        self.assertEquals(self.srv._registeredUsers['FOONODEA'][1:],
                          ('FOONODEA','1.2.3.4','5678','9'))
        self.assertEquals(self.srv._registeredUsers['FOONODEB'][1:],
                          ('FOONODEB','1.2.3.4','567','8'))
        import time
        time.sleep(2)
        PresenceServer._auto_logout_everybody()
        self.assertEquals(self.srv._registeredUsers, {})
        self.assertEquals(self.srv._ruReverseMap, {})
        self.assertEquals(self.srv._ruTimestamp, {})
        PresenceServer._autoExpirationDelayInSecs = 3600 * 24
        self.assertEquals(self.srv._autoExpirationDelayInSecs,
                          3600 * 24)

        
    def testCrashOnSameNotification(self):
        self.srv.transport = MockTransport('1.2.3.4')
        mockLineReceiver = MockLineReceiver()
        self.srv.sendLine = mockLineReceiver.sendLine
        self.assertEquals(self.srv._registeredUsers, {})
        self.assertEquals(self.srv._ruTimestamp, {})
        self.assertEquals(self.srv._ruReverseMap, {})
        # same everything
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        # same Id, diff ip/port
        self.srv.lineReceived("notify:FOONODEA:1.2.3.0:5678:9")
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        # diff Id, same ip/port (we once were crashing on this one)
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        self.srv.lineReceived("notify:FOONODEB:1.2.3.4:5678:9")


if __name__ == '__main__':
    unittest.main()
