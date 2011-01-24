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
        log_item = SyslogProtocol.decode(data)
        log_item["host"] = self.transport.getPeer()[1]
        self.queue.append(log_item)