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

from twisted.internet import protocol
from syslog_protocol import SyslogProtocol

class SyslogTCPFactory(protocol.Factory):
    noisy = 0
    numberConnections = 0
    maxNumberConnections = 256

class SyslogTCP(protocol.Protocol):
    def connectionMade(self):
        self.factory.numberConnections += 1
        if self.factory.numberConnections > self.factory.maxNumberConnections:
            self.transport.loseConnection()

    def connectionLost(self, reason):
        self.factory.numberConnections -= 1

    def dataReceived(self, data):
        for log_item in SyslogProtocol.decode(data):
            log_item["host"] = self.transport.getPeer().host
            self.factory.queue.append(log_item)
