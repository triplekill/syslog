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

import json, random, string
from twisted.web import server, resource
import lucene

class SyslogHTTP(resource.Resource):
    isLeaf = True
    clients = []
    queue = []
    q = None
    
    def write_data(self, request, data):
        size = len(data)
        if size == 0 or size > 0xffff:
            return
        else:
            request.write("%04x%s" % (size, data))
    
    def append(self, message):
        if message["message"]:

            # add to disk-based search index
            doc = lucene.Document()
            doc.add(lucene.Field("host", message["host"], lucene.Field.Store.YES, lucene.Field.Index.ANALYZED))
            doc.add(lucene.Field("message", message["message"], lucene.Field.Store.YES, lucene.Field.Index.ANALYZED))
            doc.add(lucene.Field("facility", message["facility"], lucene.Field.Store.YES, lucene.Field.Index.ANALYZED))
            doc.add(lucene.Field("priority", message["priority"], lucene.Field.Store.YES, lucene.Field.Index.ANALYZED))
            self.lucene_writer.addDocument(doc)
            # self.lucene_writer.optimize()
            
            # add to in-memory queue
            self.queue.append(message)
            if len(self.queue) > 50:
                self.queue.pop(0)

            # serve to clients
            for client in self.clients:
                if not self.q or (self.q and self.q in message["host"] or self.q in message["message"] or self.q in message["facility"] or self.q in message["priority"]):
                    self.write_data(client, json.dumps(message))

    def connectionLost(self, err, request):
        self.clients.remove(request)
    
    def get_q(self, request):
        if request.args.has_key("q"):
            return request.args["q"][0].strip()
            
    def render_GET(self, request):
        if request.path == "/stream":
            self.clients.append(request)
            request.setHeader("Connection", "Keep-Alive")
            request.setHeader("Content-Type", "application/x-syslog-stream")
            request.setHeader("Cache-Control", "no-store")
            request.setHeader("E-Tag", '"%s"' % ''.join(random.choice(string.letters) for i in xrange(32)))
            
            request.notifyFinish().addErrback(self.connectionLost, request)
            
            self.q = self.get_q(request)
            if self.q:
                self.lucene_writer.commit()
                lucene_searcher = lucene.IndexSearcher(self.lucene_writer.getReader())

                parser = lucene.MultiFieldQueryParser(lucene.Version.LUCENE_30, ["host", "message", "facility", "priority"], self.lucene_analyzer)
                query = lucene.MultiFieldQueryParser.parse(parser, self.q)
                hits = lucene_searcher.search(query, 50)

                # print "Found %d document(s) that matched query '%s':" % (hits.totalHits, query)

                for hit in hits.scoreDocs:
                    doc = lucene_searcher.doc(hit.doc)
                    data = {
                        "host": doc.get("host").encode("utf-8"),
                        "facility": doc.get("facility").encode("utf-8"),
                        "message": doc.get("message").encode("utf-8"),
                        "priority": doc.get("priority").encode("utf-8")
                    }
                    self.write_data(request, json.dumps(data))
            else:
                for data in self.queue:
                    self.write_data(request, json.dumps(data))

            return server.NOT_DONE_YET
        else:
            return open("index.html").read()
