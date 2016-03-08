#-*- coding: UTF-8 -*-
import os
import sys
from twisted.internet import reactor
from twisted.web import proxy, server

if len(sys.argv) == 4:
    site = server.Site(proxy.ReverseProxyResource(sys.argv[1], int(sys.argv[2]), ''))
    reactor.listenTCP(int(sys.argv[3]), site)
    reactor.run()
else:
    print len(sys.argv)
