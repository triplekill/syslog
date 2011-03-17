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
    sock.sendto(data, (host, port))
    sock.close()

def syslog_tcp(message, priority=0, facility=0, host='127.0.0.1', port=514):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    data = SyslogProtocol.encode(facility, priority, message)
    sock.send(data)
    sock.close()

import getopt

def usage():
    print 'usage: %s [-f <facility>] [-p <priority>] [-c <count>] [-d <delay>] [-h <host>] -m <message>'

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:p:m:c:d:h:")
    except getopt.GetoptError, err:
        print str(err) # will print something like "option -a not recognized"
        sys.exit(2)

    f = 0 # facility
    p = 0 # priority
    m = "" # message
    c = 1 # count
    d = 0.01 # delay
    h = '127.0.0.1' # host

    for o, a in opts:
        if o == "-f":
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
            h = a
        else:
            assert False, "unhandled option"

    if not m:
        usage()

    for i in range(0, c):
        syslog_udp("%d\t%s" % (i, m), p, f, h, 5140)
        time.sleep(d)
