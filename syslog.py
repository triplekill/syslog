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

def syslog(message, priority=0, facility=0, host='localhost', port=514):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = SyslogProtocol.encode(facility, priority, message)
    sock.sendto(data, (host, port))
    sock.close()

if __name__ == "__main__":
    i = 0
    # while True:
    #     priority = random.randint(0, 7)
    #     facility = random.randint(0, 23)
    #     message = ("test %06d " % i) + "+" * random.randint(0, 250)
    #     syslog(message, priority, facility, host='localhost')
    #     time.sleep(0.01)
    #     i += 1
    syslog(sys.argv[1], host='localhost')
