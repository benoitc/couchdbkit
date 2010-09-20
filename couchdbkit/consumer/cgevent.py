# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import traceback


from couchdbkit.consumer.base import check_callable
from couchdbkit.consumer.sync import SyncConsumer
from couchdbkit.utils import json

import gevent
from gevent import monkey 

from gevent import socket
from gevent import select


class ChangeConsumer(gevent.Greenlet):
    def __init__(self, db, callback=None, **params):
        gevent.Greenlet.__init__(self)
        self.process_change = callback
        self.params = params
        self.db = db

    def _run(self):
        while True:
            try:
                resp = self.db.res.get("_changes", **self.params)
                return self.consume(resp)
            except (SystemExit, KeyboardInterrupt):
                gevent.sleep(5)
            except:
                traceback.print_exc()
                gevent.sleep(5)

    def consume(self, resp):
        raise NotImplementedError

class ContinuousChangeConsumer(ChangeConsumer):

    def consume(self, resp):
        with resp.body_stream() as body:
            while True:
                line = body.readline()
                if not line:
                    break
                if line.endswith("\r\n"):
                    line = line[:-2]
                else:
                    line = line[:-1]
                self.process_change(line)

class LongPollChangeConsumer(ChangeConsumer):

    def consume(self, resp):
        with resp.body_stream() as body:
            buf = []
            while True:
                data = body.read()
                if not data:
                    break
                buf.append(data)
                gevent.sleep(0.1)
            change = "".join(buf)
            try:
                change = json.loads(change)
            except ValueError:
                pass 
            self.process_change(change)


class GeventConsumer(SyncConsumer):
    def __init__(self, db):
        monkey.patch_socket()
        super(GeventConsumer, self).__init__(db)

    def fetch(self, cb=None, **params):
        if cb is None:
            return super(GeventConsumer, self).wait_once(**params)
        resp = self.db.res.get("_changes", **params)
        gevent.spawn(cb, resp.json_body).join()
        
    def wait_once(self, cb=None, **params):
        if cb is None:
            return super(GeventConsumer, self).wait_once(**params)

        check_callable(cb)
        params.update({"feed": "longpoll"})
        ret = LongPollChangeConsumer.spawn(self.db, callback=cb,
                **params).join()
        if cb is None:
            return ret

    def wait(self, cb, **params):
        params.update({"feed": "continuous"})
        ContinuousChangeConsumer.spawn(self.db, callback=cb, 
                **params).join()
        

