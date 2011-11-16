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

from syslog_protocol import SyslogProtocol
import socket, sys, random, time

def syslog_udp(message, priority=0, facility=0, host='127.0.0.1', port=514):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print "syslog_udp " + message
    data = SyslogProtocol.encode(facility, priority, message)
    sock.sendto(data + '\n', (host, port))
    sock.close()

def syslog_tcp_open(host='127.0.0.1', port=514):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    return sock

def syslog_tcp(sock, message, priority=0, facility=0):
    print "syslog_tcp " + message
    data = SyslogProtocol.encode(facility, priority, message)
    sock.send(data + '\n')

def syslog_tcp_close(sock):
    sock.close()

import getopt

def usage():
    print 'usage: %s [-t [udp|tcp]] [-f <facility>] [-p <priority>] [-c <count>] [-d <delay>] [-h <host>[:<port>]] -m <message>' % sys.argv[0]

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "t:f:p:m:c:d:h:")
    except getopt.GetoptError, err:
        print str(err) # will print something like "option -a not recognized"
        sys.exit(2)

    f = 0 # facility
    p = 0 # priority
    m = "" # message
    c = 1 # count
    d = 0.01 # delay
    h = '127.0.0.1' # host
    port = 5140
    t = 'udp'

    for o, a in opts:
        if o == "-t":
            if a == 'tcp':
                t = a
        elif o == "-f":
            f = int(a)
        elif o == "-p":
            p = int(a)
        elif o == "-m":
            m = a
        elif o == "-c":
            c = int(a)
        elif o == "-d":
            d = float(a)
        elif o == "-h":
            if a.find(':'):
              h, port = a.split(':')
              port = int(port)
            else:
              h = a
        else:
            assert False, "unhandled option"

    if not m:
        usage()
        sys.exit(-1)

    if t == 'udp':
        for i in range(0, c):
            syslog_udp("%s (%d)" % (m, i), p, f, h, port)
            time.sleep(d)
    elif t == 'tcp':
        sock = syslog_tcp_open(h, port)
        for i in range(0, c):
            syslog_tcp(sock, "%s (%d)" % (m, i), p, f)
            time.sleep(d)
        syslog_tcp_close(sock)
