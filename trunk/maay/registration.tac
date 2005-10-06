#!/usr/bin/twistd2.3 -noy 

from twisted.application import service, internet
from twisted.internet.protocol import ServerFactory

from maay.registration import RegistrationServer

application = service.Application("registrationServer")
factory = ServerFactory()
factory.protocol = RegistrationServer
internet.TCPServer(2345, factory, interface='127.0.0.1').setServiceParent(application)
