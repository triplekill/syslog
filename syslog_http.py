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

import json, random, string, time, datetime
from twisted.web import server, resource
import lucene

class SyslogHTTP(resource.Resource):
    
    items_per_page = 50
    isLeaf = True
    clients = []
    q = None
    
    def send_data(self, request, data):
        size = len(data)
        if size == 0 or size > 0xffff:
            return
        else:
            request.write("%04x%s" % (size, data))

    def send_document(self, request, document):
        data = {
            "host": document.get("host").encode("utf-8"),
            "datetime": document.get("datetime").encode("utf-8"),
            "facility": document.get("facility").encode("utf-8"),
            "message": document.get("message").encode("utf-8"),
            "priority": document.get("priority").encode("utf-8")
        }
        self.send_data(request, json.dumps(data))

    def append(self, message):
        if message["message"]:
            
            # add to disk-based search index
            message["datetime"] = int(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            print message["datetime"]

            doc = lucene.Document()
            doc.add(lucene.Field("host", message["host"], lucene.Field.Store.YES, lucene.Field.Index.NOT_ANALYZED))
            doc.add(lucene.NumericField("datetime").setLongValue(message["datetime"]))
            doc.add(lucene.Field("message", message["message"], lucene.Field.Store.YES, lucene.Field.Index.ANALYZED))
            doc.add(lucene.Field("facility", message["facility"], lucene.Field.Store.YES, lucene.Field.Index.NOT_ANALYZED))
            doc.add(lucene.Field("priority", message["priority"], lucene.Field.Store.YES, lucene.Field.Index.NOT_ANALYZED))
            self.lucene_writer.addDocument(doc)
            
            # serve to clients
            if len(self.clients) > 0:
                self.lucene_writer.commit()

            for client in self.clients:
                if not self.q or (self.q and self.q in message["host"] or self.q in message["message"] or self.q in message["facility"] or self.q in message["priority"]):
                    self.send_data(client, json.dumps(message))

    def connectionLost(self, err, request):
        self.clients.remove(request)
    
    def get_argument(self, arg, request):
        if request.args.has_key(arg):
            return request.args[arg][0].strip()
    

    def render_GET(self, request):
        if request.path == "/stream":
            self.clients.append(request)
            request.notifyFinish().addErrback(self.connectionLost, request)

            request.setHeader("Connection", "Keep-Alive")
            request.setHeader("Content-Type", "application/x-syslog-stream")
            request.setHeader("Cache-Control", "no-store")
            request.setHeader("E-Tag", '"%s"' % ''.join(random.choice(string.letters) for i in xrange(32)))
            
            self.q = self.get_argument('q', request)
            if self.q:
                lucene_searcher = lucene.IndexSearcher(self.lucene_writer.getReader())
                parser = lucene.MultiFieldQueryParser(lucene.Version.LUCENE_30, ["host", "message", "facility", "priority"], self.lucene_analyzer)
                query = lucene.MultiFieldQueryParser.parse(parser, self.q)
                hits = lucene_searcher.search(query, None, self.items_per_page, lucene.Sort(lucene.SortField("datetime", lucene.SortField.INTEGER)))

                for hit in hits.scoreDocs:
                    document = lucene_searcher.doc(hit.doc)
                    self.send_document(request, document)

            else:
                self.lucene_writer.commit()
                reader = self.lucene_writer.getReader()

                documents = []
                i = reader.numDocs()
                j = 0
                while i > 0:
                    i -= 1
                    if not reader.isDeleted(i):
                        j += 1
                        document = reader.document(i);
                        documents.insert(0, document)
                        if j >= self.items_per_page:
                            break
                
                for document in documents:
                    self.send_document(request, document)

            return server.NOT_DONE_YET
        else:
            return open("index.html").read()
