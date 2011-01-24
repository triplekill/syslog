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
