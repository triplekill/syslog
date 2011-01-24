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

import json
from twisted.web import server, resource

class SyslogHTTP(resource.Resource):
    isLeaf = True
    clients = []
    queue = []
    
    def write_data(self, request, data):
        size = len(data)
        if size == 0 or size > 0xffff:
            return
        request.write("%04x%s" % (size, data))
    
    def append(self, message):
        if len(message["message"]) == 0:
            return
        data = json.dumps(message)
        self.queue.append(data)
        if len(self.queue) > 50:
            self.queue.pop(0)
        
        for client in self.clients:
            self.write_data(client, data)

    def connectionLost(self, err, request):
        self.clients.remove(request)
    
    def render_GET(self, request):
        if request.path == "/stream":
            self.clients.append(request)
            request.setHeader("Connection", "Keep-Alive")
            request.setHeader("Content-Type", "application/x-syslog-stream")
            request.notifyFinish().addErrback(self.connectionLost, request)
            
            for data in self.queue:
                self.write_data(request, data)

            return server.NOT_DONE_YET
        else:
            return open("index.html").read()
