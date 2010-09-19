# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import asyncore
import asynchat
import socket
import sys

from couchdbkit.consumer.base import ConsumerBase, check_callable
from couchdbkit.utils import json

__all__ = ['SyncConsumer']

class SyncConsumer(ConsumerBase):

    def wait_once(self, cb=None, **params):
        if cb is not None:
            check_callable(cb)

        params.update({"feed": "longpoll"})
        resp = self.db.res.get("_changes", **params)
        buf = ""
        with resp.body_stream() as body:
            while True:
                data = body.read()
                if not data: 
                    break
                buf += data
            
            ret = json.loads(buf)
            if cb is not None:
                cb(ret)
                return

            return ret
        
    def wait(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "continuous"})
        resp = self.db.res.get("_changes", **params)
        
        if resp.headers.get('transfer-encoding') == "chunked":
            chunked = True
        else:
            chunked = False
        
        change_handler = continuous_changes_handler(resp, cb, 
                chunked)
        asyncore.loop()

        
        
class continuous_changes_handler(asynchat.async_chat):
    
    def __init__(self, resp, callback, chunked):
        self.resp = resp
        self.callback = callback
        self.chunked = chunked

        buf = resp.response.body.reader.unreader.buf.getvalue()

        self.buf = [buf]
        self.sock = sock = resp.response.body.reader.unreader.sock
        asynchat.async_chat.__init__(self, sock=sock)
        
        if self.chunked:
            self.set_terminator("\r\n")
        else:
            self.set_terminator("\n")
            
        data = resp.response.body.reader.buf.getvalue()
        self.buf.append(data)

        self.chunk_left = False        
        
    def handle_close(self):
    
        self.close()
        
    def collect_incoming_data(self, data):
        if not data: return
        if self.chunked:
            if not self.chunk_left:
                return
                
            self.buf.append(data)
        else:
            self.buf.append(data)
            
    def emit_line(self, line):
        line = json.loads(line)
        self.callback(line)
            
    def found_terminator(self):
        if self.chunked and not self.chunk_left:
            # we got the length
            self.chunk_left = True
            self.buf = []
            return
            
        line = "".join(self.buf)
        self.buf = []
        if self.chunked: 
            self.chunk_left = False
            line = line.strip()

        if line:
            self.emit_line(line)
