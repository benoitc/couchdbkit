# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import anyjson
import asyncore
import asynchat
import socket
import sys

class Consumer(object):
    """ Database change consumer
    
    Example Usage:
    
        >>> from couchdbkit import Server, Consumer
        >>> s = Server()
        >>> db = s['testdb']
        >>> c = Consumer(db)
        >>> def print_line(line):
        ...     print "got %s" % line
        ... 
        >>> c.register_callback(print_line)
        >>> c.wait() # Go into receive loop
         
    """
    
    def __init__(self, db):
        self.db = db
        self.callbacks = []
        self._resp = None

    def register_callback(self, callback):
        """ Register a callback on which changes will
        be sent with `wait_once` and `wait`methods. 
        """
        
        if not callable(callback):
            raise TypeError("callback isn't a callable")
        self.callbacks.append(callback)

    def fetch(self, **params):
        """ Fetch all changes and return. If since is specified, fetch all changes
        since this doc sequence
        
        Args:
        @param params: kwargs
        See Changes API (http://wiki.apache.org/couchdb/HTTP_database_API#Changes)
        
        @return: dict, change result
        
        """
        resp = self.db.res.get("_changes", **params)
        return resp.json_body
        
    def wait_once(self, **params):
        """Wait for one change and return (longpoll feed) 
        
        Args:
        @param params: kwargs
        See Changes API (http://wiki.apache.org/couchdb/HTTP_database_API#Changes)
        
        @return: dict, change result
        """
        params.update({"feed": "longpoll"})
        resp = self.db.res.get("_changes", **params)
        buf = ""
        with resp.body_stream() as body:
            while True:
                data = body.read()
                if not data: 
                    break
                buf += data
            
            ret = anyjson.deserialize(buf)
            for callback in self.callbacks:
                callback(ret)
            return ret
        
    def wait(self, **params):
        """ Wait for changes until the connection close (continuous feed)
        
        Args:
        @param params: kwargs
        See Changes API (http://wiki.apache.org/couchdb/HTTP_database_API#Changes)
        
        @return: dict, line of change
        """
        params.update({"feed": "continuous"})
        self.resp = resp = self.db.res.get("_changes", **params)
        
        if resp.headers.get('transfer-encoding') == "chunked":
            chunked = True
        else:
            chunked = False
        
        change_handler = continuous_changes_handler(resp, self.callbacks, 
                                                    chunked)
        asyncore.loop()

        
        
class continuous_changes_handler(asynchat.async_chat):
    
    def __init__(self, resp, callbacks, chunked):
        self.resp = resp
        self.callbacks = callbacks
        self.chunked = chunked
        
        
        self.buf = []
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
        line = anyjson.deserialize(line)
        for callback in self.callbacks:
            callback(line)
            
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