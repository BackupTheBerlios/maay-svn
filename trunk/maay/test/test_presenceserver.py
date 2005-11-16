#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

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
        self.assertEquals(self.srv._ruReverseMap, {('1.2.3.4', '5678') : 'FOONODEA',
                                                   ('1.2.3.4', '567') : 'FOONODEB',})


    def testNotifyTwice(self):
        self.srv.transport = MockTransport('1.2.3.4')
        self.assertEquals(self.srv._registeredUsers, {})
        self.assertEquals(self.srv._ruReverseMap, {})
        self.srv.lineReceived("notify:FOONODEA:1.2.3.4:5678:9")
        self.srv.lineReceived("notify:FOONODEB:1.2.3.4:5678:9")
        self.assertEquals(self.srv._registeredUsers['FOONODEB'][1:],
                          ('FOONODEB','1.2.3.4','5678','9'))
        self.assertEquals(self.srv._ruReverseMap[('1.2.3.4','5678')],
                          'FOONODEB')
        

if __name__ == '__main__':
    unittest.main()
