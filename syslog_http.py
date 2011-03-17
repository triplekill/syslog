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

import json, random, string, time, datetime, os
from twisted.web import server, resource
import lucene

class SyslogHTTP(resource.Resource):
    
    items_per_page = 50
    isLeaf = True
    clients = []
    q = None
    
    # log fall-back
    log_filename = None
    log_handle = None

    def log_get_filename(self):
        return 'tmp/log_%s' % datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
        
    def log_init_handle(self):
        current_filename = self.log_get_filename()
        if not self.log_filename or self.log_filename != current_filename:
            if self.log_handle:
                self.log_handle.close()
            self.log_handle = open(self.log_get_filename(), 'a')
            self.log_filename = current_filename
    
    def log_append(self, string):
        self.log_init_handle()
        self.log_handle.write(string + '\n')
    
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

    def tokenize(self, string):
        tokens = set([])
        if string:
            tokenStream = self.lucene_analyzer.tokenStream("contents", lucene.StringReader(string))
            term = tokenStream.addAttribute(lucene.TermAttribute.class_)
            while tokenStream.incrementToken():
                tokens.add(term.term())
        return tokens

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

            # write to logfile
            self.log_append(str(message))

            # write to index
            self.lucene_writer.addDocument(doc)
            
            # serve to clients
            if len(self.clients) > 0:
                self.lucene_writer.commit()

            for client in self.clients:
                doc_tokens = self.tokenize(message["message"])
                doc_tokens = doc_tokens.union(set([message["host"], message["facility"], message["priority"]]))

                query_tokens = self.tokenize(self.q)
                matching_tokens = query_tokens.intersection(doc_tokens)
                
                # update client when query is empty or when a query_token matches a doc_token
                if not self.q or matching_tokens:
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

        elif request.path == "/log":
            # request.setHeader('Content-Disposition', 'attachment; filename="syslog.log"')
            request.setHeader('Content-Type', 'text/plain')
            self.log_init_handle()
            self.log_handle.flush()
            f = None
            try:
                f = open(self.log_get_filename())
            except IOError:
                return ''
            lines = f.readlines()
            f.close()
            lines.reverse()
            return ''.join(lines)

        else:
            return open("index.html").read()
