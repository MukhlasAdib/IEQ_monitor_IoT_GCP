from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
import socketserver
import urllib.parse

### Handling HTTP Request
class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        with open('live_log.txt','r') as f:
            msg = f.read()
        self.send_response(200)
        self.send_header('Content-Type','text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(msg.encode('utf-8'))

PORT = 8080
webServer = HTTPServer(('',8080),WebHandler)
webServer.serve_forever()