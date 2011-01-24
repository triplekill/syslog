#!/usr/bin/env python

from syslog_protocol import SyslogProtocol
import socket, sys, random, time

def syslog(message, priority="notice", facility="daemon", host='localhost', port=514):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data = SyslogProtocol.encode(facility, priority, message)
    sock.sendto(data, (host, port))
    sock.close()

if __name__ == "__main__":
    i = 0
    while True:
        priority = random.randint(0, 7)
        facility = random.randint(0, 23)
        message = ("%06d " % i) + "+" * random.randint(0, 250)
        syslog(message, priority, facility, host='localhost')
        time.sleep(0.001)
        i += 1
    # syslog("test", host='localhost')
