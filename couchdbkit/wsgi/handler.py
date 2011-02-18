# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import sys
import StringIO
import traceback
from urllib import unquote

from restkit.util import url_encode

from .. import __version__
from ..external import External

def _normalize_name(name):
    return  "-".join([w.lower().capitalize() for w in name.split("-")])

class WSGIRequest(object):
    
    SERVER_VERSION = "couchdbkit/%s" % __version__
    
    def __init__(self, line):
        self.line = line
        self.response_status = 200
        self.response_headers = {}
        self.start_response_called = False
    
    def read(self):
        headers = self.parse_headers()
        
        length = headers.get("CONTENT_LENGTH")
        if self.line["body"] and self.line["body"] != "undefined":
            length = len(self.line["body"])
            body = StringIO.StringIO(self.line["body"])
            
        else:
            body = StringIO.StringIO()
            
        # path
        script_name, path_info = self.line['path'][:2],  self.line['path'][2:]
        if path_info:
            path_info = "/%s" % "/".join(path_info)
        else: 
            path_info = ""
        script_name = "/%s" % "/".join(script_name)

        # build query string
        args = []
        query_string = None
        for k, v in self.line["query"].items():
            if v is None:
                continue
            else:
                args.append((k,v))       
        if args: query_string = url_encode(dict(args))
        
        # raw path could be useful
        path = "%s%s" % (path_info, query_string)
                
        # get server address
        if ":" in self.line["headers"]["Host"]:
            server_address = self.line["headers"]["Host"].split(":")
        else:
            server_address = (self.line["headers"]["Host"], 80)

        environ = {
            "wsgi.url_scheme": 'http',
            "wsgi.input": body,
            "wsgi.errors": StringIO.StringIO(),
            "wsgi.version": (1, 0),
            "wsgi.multithread": False,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
            "SCRIPT_NAME": script_name,
            "SERVER_SOFTWARE": self.SERVER_VERSION,
            "COUCHDB_INFO": self.line["info"],
            "COUCHDB_REQUEST": self.line,
            "REQUEST_METHOD": self.line["verb"].upper(),
            "PATH_INFO": unquote(path_info),
            "QUERY_STRING": query_string,
            "RAW_URI": path,
            "CONTENT_TYPE": headers.get('CONTENT-TYPE', ''),
            "CONTENT_LENGTH": length,
            "REMOTE_ADDR": self.line['peer'],
            "REMOTE_PORT": 0,
            "SERVER_NAME": server_address[0],
            "SERVER_PORT": int(server_address[1]),
            "SERVER_PROTOCOL": "HTTP/1.1"
        }
        
        for key, value in headers.items():
            key = 'HTTP_' + key.replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value
                
        return environ
        
    def start_response(self, status, response_headers):
        self.response_status = int(status.split(" ")[0])
        for name, value in response_headers:
            name = _normalize_name(name)
            self.response_headers[name] = value.strip()
        self.start_response_called = True
                
    def parse_headers(self):
        headers = {}
        for name, value in self.line.get("headers", {}).items():
            name = name.strip().upper().encode("utf-8")
            headers[name] = value.strip().encode("utf-8")
        return headers

class WSGIHandler(External):
    
    def __init__(self, application, stdin=sys.stdin, 
            stdout=sys.stdout):
        External.__init__(self, stdin=stdin, stdout=stdout)
        self.app = application
    
    def handle_line(self, line):
        try:
            req = WSGIRequest(line)
            response = self.app(req.read(), req.start_response)
        except:
            self.send_response(500, "".join(traceback.format_exc()), 
                    {"Content-Type": "text/plain"})
            return 
            
        content = "".join(response).encode("utf-8")    
        self.send_response(req.response_status, content, req.response_headers)
    
    
