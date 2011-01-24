#!/usr/bin/env python
# Python-based syslog server with server-push web frontend
# Copyright (C) 2011 Henning Peters <pete@dexterslab.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
