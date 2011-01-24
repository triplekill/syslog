#!/usr/bin/env python

import sys, os.path
from twisted.web import server
from twisted.internet import reactor
from syslog_http import SyslogHTTP
from syslog_udp import SyslogUDP
from syslog_tcp import SyslogTCP, SyslogTCPFactory

if __name__ == "__main__":
    
    # enable HTTP
    http = SyslogHTTP()
    site = server.Site(http)
    reactor.listenTCP(8080, site)

    # enable TCP
    tcp = SyslogTCPFactory()
    tcp.protocol = SyslogTCP
    tcp.queue = http
    reactor.listenTCP(514, tcp)

    # enable UDP
    udp = SyslogUDP()
    udp.queue = http
    reactor.listenUDP(514, udp)

    reactor.run()
