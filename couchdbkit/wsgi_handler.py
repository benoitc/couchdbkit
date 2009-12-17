# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import re
import sys
import StringIO
import traceback
from urllib import unquote

from restkit.utils import url_encode

from couchdbkit import __version__
from couchdbkit.external import External

def _normalize_name(name):
    return "-".join([w.capitalize() for w in name.split("-")])

class WSGIRequest(object):
    
    SERVER_VERSION = "couchdbkit/%s" % __version__
    
    def __init__(self, line):
        self.line = line
        self.response_status = 500
        self.response_headers = {}
        self.response_headers.setdefault("Content-Type", "text/plain")
        self.start_response_called = False
    
    def read(self):
        headers = self.parse_headers()
        
        length = None
        if self.line["body"] and self.line["body"] != "undefined":
            body = StringIO.StringIO(self.line["body"])
            length = len(body)
        else:
            body = StringIO.StringIO()
            
        # path
        path_info = unquote("/".join(self.line["path"]))
        
        # buikd query string
        params = []
        retval = []
        for k, v in self.line["query"].items():
            if v is None:
                continue
            else:
                params.append((k,v))
                
        if params:  retval = ['?', url_encode(dict(params))]
        query_string = "".join(retval)
        
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
            "wsgi.errors": sys.stderr,
            "wsgi.version": (1, 0),
            "wsgi.multithread": False,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
            "SCRIPT_NAME": "",
            "SERVER_SOFTWARE": self.SERVER_VERSION,
            "COUCHDB_INFO": self.line["info"],
            "COUCHDB_REQUEST": self.line,
            "REQUEST_METHOD": self.line["verb"].upper(),
            "PATH_INFO": unquote(path_info),
            "QUERY_STRING": query_string,
            "RAW_URI": path,
            "CONTENT_TYPE": headers.get('content-type', ''),
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
            self.response_headers[_normalize_name(name)] = str(value)
        self.start_response_called = True
                
    def parse_headers(self):
        headers = self.line.get("headers", {})
        for name, value in headers.items():
            headers[name.strip().upper()] = value.strip()
        return headers

class WSGIHandler(External):
    
    def __init__(self, application, stdin=sys.stdin, 
            stdout=sys.stdout):
        External.__init__(self, stdin=stdin, stdout=stdout)
        self.app = application
    
    def handle_line(self, line):
        req = WSGIRequest(line)
        try:
            response = self.app(req.read(), req.start_response)
        except:
            response = traceback.format_exc()  
        self.send_response(req.response_status, "".join(response), 
            req.response_headers)
    
    