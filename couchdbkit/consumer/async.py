# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.


from couchdbkit.consumer.base import ConsumerBase, check_callable
from couchdbkit.utils import json


class AsyncConsumer(ConsumerBase):

    def __init__(self, db, spawn=None):
        ConsumerBase.__init__(self, db)
        self.spawn = spawn


    # functions you could ovveride

    def sleep(self, t):
        return

    def wait_read(self, sock):
        raise NotImplementedError

    def patch_socket(self, sock):
        return sock 


    ####################################
    # main functions
    ####################################

    def handle(self, cb, line):
        try:
            line = json.loads(line)
        except ValueError:
            pass
        cb(line)


    def wait_once(self, cb=None, **params):
        if cb is not None:
            check_callable(cb)

        params.update({"feed": "longpoll"})
        resp = self.db.res.get("_changes", **params)
        
        with resp.body_stream() as body:
            sock = self.patch_socket(body.reader.unreader.sock)
            body.reader.unreader.sock = sock
            try:
                while True:
                    if self.wait_read(sock):
                        buf = []
                        while True:
                            chunk = body.read()
                            if not chunk:
                                break
                            buf.append(chunk)

                        if cb is not None:
                            self.spawn(self.handle, cb, "".join(buf))
                            self.sleep(0.1)
                        else:
                            ret = "".join(buf)
                            try:
                                return json.loads(ret)
                            except ValueError:
                                return ret
                        break 
            except (SystemExit, KeyboardInterrupt):
                pass
                        
    def wait(self, cb, **params):
        params.update({"feed": "continuous"})
        resp = self.db.res.get("_changes", **params)
        
        if resp.headers.get('transfer-encoding') == "chunked":
            self.chunked = True
        else:
            self.chunked = False

        with resp.body_stream() as body:
            sock = self.patch_socket(body.reader.unreader.sock)
            body.reader.unreader.sock = sock
            sock.setblocking(0)

            # read all buf if possible
            buf = resp.response.body.reader.unreader.buf.getvalue()
            resp.response.body.reader.unreader.buf.truncate(0)
            body.buf.write(buf)
            
            try:
                while True:
                    if self.wait_read(sock):
                        line = body.readline()
                        if not line:
                            break
                        if line.endswith("\r\n"):
                            line = line[:-2]
                        else:
                            line = line[:-1]
                        if not line:
                            continue

                        self.spawn(self.handle, cb, line)
                    self.sleep(0.1)
            except (KeyboardInterrupt, SystemExit):
                pass

    
