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
from twisted.internet import reactor
import lucene
from syslog_protocol import SyslogProtocol

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
        dt = data['timestamp']
        
        json_data = json.dumps(data)
        size = len(json_data)
        if size == 0 or size > 0xffff:
            return
        else:
            request.write("%04x%s" % (size, json_data))

    def send_document(self, request, document):
        data = {
            'type': 'document',
            'host': document.get('host').encode('utf-8'),
            'timestamp': document.get('timestamp').encode('utf-8'),
            'facility': document.get('facility').encode('utf-8'),
            'message': document.get('message').encode('utf-8'),
            'priority': document.get('priority').encode('utf-8')
        }
        self.send_data(request, data)

    def send_timestamp(self, request, timestamp, values):
        data = {
            'type': 'timestamp',
            'timestamp': timestamp,
            'values': values
        }
        self.send_data(request, data)

    def tokenize(self, string):
        tokens = set([])
        if string:
            tokenStream = self.lucene_analyzer.tokenStream('contents', lucene.StringReader(string))
            term = tokenStream.addAttribute(lucene.TermAttribute.class_)
            while tokenStream.incrementToken():
                tokens.add(term.term())
        return tokens
            
    def append(self, data):
        if data['message']:

            # current time is considered more precise than one contained in the message
            data['timestamp'] = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            data['type'] = 'document'

            doc = lucene.Document()
            doc.add(lucene.Field('host', data['host'], lucene.Field.Store.YES, lucene.Field.Index.NOT_ANALYZED))
            doc.add(lucene.NumericField('timestamp', lucene.Field.Store.YES, True).setLongValue(long(data['timestamp'])))
            doc.add(lucene.Field('facility', data['facility'], lucene.Field.Store.YES, lucene.Field.Index.NOT_ANALYZED))
            doc.add(lucene.Field('priority', data['priority'], lucene.Field.Store.YES, lucene.Field.Index.NOT_ANALYZED))
            doc.add(lucene.Field('message', data['message'], lucene.Field.Store.YES, lucene.Field.Index.ANALYZED))

            # write to logfile
            self.log_append(str(data))

            # write to index
            self.lucene_writer.addDocument(doc)
            
            # serve to clients
            if len(self.clients) > 0:
                self.lucene_writer.commit()

            for client in self.clients:
                doc_tokens = self.tokenize(data['message'])
                doc_tokens = doc_tokens.union(set([data['host'], data['facility'], data['priority']]))

                query_tokens = self.tokenize(self.q)
                matching_tokens = query_tokens.intersection(doc_tokens)
                
                # update client when query is empty or when a query_token matches a doc_token
                if not self.q or matching_tokens:
                    self.send_data(client, data)

    def connectionLost(self, err, request):
        self.clients.remove(request)
    
    def get_argument(self, arg, request):
        if request.args.has_key(arg):
            return request.args[arg][0].strip()

    def render_GET(self, request):
        if request.path == '/stream':
            self.clients.append(request)
            request.notifyFinish().addErrback(self.connectionLost, request)

            request.setHeader('Connection', 'Keep-Alive')
            request.setHeader('Content-Type', 'application/x-syslog-stream')
            request.setHeader('Cache-Control', 'no-store')
            request.setHeader('E-Tag', '"%s"' % ''.join(random.choice(string.letters) for i in xrange(32)))
            
            self.q = self.get_argument('q', request)
            # self.q = 'test'
            # 
            # if self.q:
            lucene_searcher = lucene.IndexSearcher(self.lucene_writer.getReader())
            parser = lucene.MultiFieldQueryParser(lucene.Version.LUCENE_30, ['host', 'message', 'facility', 'priority'], self.lucene_analyzer)
            query = lucene.MultiFieldQueryParser.parse(parser, self.q)
            filter = None
            # filter = lucene.NumericRangeFilter.newLongRange('timestamp', lucene.Long(long(20110318012732)), lucene.Long(long(20110318012732)), True, True)
            hits = lucene_searcher.search(query, filter, 1000, lucene.Sort(lucene.SortField('timestamp', lucene.SortField.LONG)))
            
            dates = {}
            now = long(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            now /= 1000000
            old_timestamp = None
            values = [0] * 8

            print hits.totalHits
            for hit in hits.scoreDocs:
                document = lucene_searcher.doc(hit.doc)
                
                self.send_document(request, document)
            
            
                timestamp = long(document.get('timestamp')) / 1000000
                if old_timestamp and timestamp != old_timestamp:
                    print old_timestamp, repr(values)
                    self.send_timestamp(request, old_timestamp, values)
                    # debugging slow output
                    # reactor.doSelect(1)
                    # time.sleep(0.1)
                    values = [0] * 8
                
                priority_number = SyslogProtocol.PRIORITY_REVERSE[document.get('priority')]
                values[priority_number] += 1
                old_timestamp = timestamp

            print old_timestamp, repr(values)
            self.send_timestamp(request, old_timestamp, values)
                

            # else:
            #     self.lucene_writer.commit()
            #     reader = self.lucene_writer.getReader()
            #     
            #     i = reader.numDocs()
            #     j = 0
            #     while i > 0:
            #         i -= 1
            #         if not reader.isDeleted(i):
            #             j += 1
            #             document = reader.document(i);
            #             documents.insert(0, document)
            #             if j < self.items_per_page:
            #                 self.send_document(request, document)

            return server.NOT_DONE_YET

        elif request.path == '/log':
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

        elif request.path == '/jquery.js':
            request.setHeader('Content-Type', 'text/javascript')
            return open('jquery.js').read()
        elif request.path == '/raphael.js':
            request.setHeader('Content-Type', 'text/javascript')
            return open('raphael.js').read()
        else:
            request.setHeader('Content-Type', 'text/html')
            return open('index.html').read()
