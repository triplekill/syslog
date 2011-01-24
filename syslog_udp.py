from twisted.internet import protocol
from syslog_protocol import SyslogProtocol

class SyslogUDP(protocol.DatagramProtocol):
    def datagramReceived(self, data, (host, port)):
        log_item = SyslogProtocol.decode(data)
        log_item["host"] = host
        self.queue.append(log_item)
