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

import lucene
from AnalyzerUtils import *

syslog_udp_port = 5140
syslog_tcp_port = 5140
syslog_http_port = 8080

if __name__ == "__main__":

    # enable lucene, create index if it doesn't exist, yet
    lucene.initVM()
    lucene_dir = lucene.SimpleFSDirectory(lucene.File("tmp"))
    lucene_analyzer = lucene.WhitespaceAnalyzer(lucene.Version.LUCENE_30)
    lucene_writer = lucene.IndexWriter(lucene_dir, lucene_analyzer, lucene.IndexWriter.MaxFieldLength(1024))

    # enable HTTP
    http = SyslogHTTP()
    http.lucene_writer = lucene_writer
    http.lucene_dir = lucene_dir
    http.lucene_analyzer = lucene_analyzer
    site = server.Site(http)
    reactor.listenTCP(syslog_http_port, site)
    print "listening for syslog on UDP port %d" % syslog_udp_port

    # enable TCP
    tcp = SyslogTCPFactory()
    tcp.protocol = SyslogTCP
    tcp.queue = http
    reactor.listenTCP(syslog_tcp_port, tcp)
    print "listening for syslog on TCP port %d" % syslog_tcp_port

    # enable UDP
    udp = SyslogUDP()
    udp.queue = http
    reactor.listenUDP(syslog_udp_port, udp)
    print "listening for HTTP on port %d" % syslog_http_port

    reactor.run()
