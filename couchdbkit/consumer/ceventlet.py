# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

import traceback

import eventlet
from eventlet import event

from .base import check_callable
from .sync import SyncConsumer
from ..utils import json


class ChangeConsumer(object):
    def __init__(self, db, callback, **params):
        self.process_change = callback
        self.params = params
        self.db = db
        self.stop_event = event.Event()

    def wait(self):
        eventlet.spawn_n(self._run)
        self.stop_event.wait()

    def wait_async(self):
        eventlet.spawn_n(self._run)

    def _run(self):
        while True:
            try:
                resp = self.db.res.get("_changes", **self.params)
                return self.consume(resp)
            except (SystemExit, KeyboardInterrupt):
                eventlet.sleep(5)
                break
            except:
                traceback.print_exc()
                eventlet.sleep(5)
                break
        self.stop_event.send(True)

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
                if not line:
                    continue
                self.process_change(line)
            self.stop_event.send(True)


class LongPollChangeConsumer(ChangeConsumer):

    def consume(self, resp):
        with resp.body_stream() as body:
            buf = []
            while True:
                data = body.read()
                if not data:
                    break
                buf.append(data)
            change = "".join(buf)
            try:
                change = json.loads(change)
            except ValueError:
                pass
            self.process_change(change)
            self.stop_event.send(True)


class EventletConsumer(SyncConsumer):
    def __init__(self, db):
        eventlet.monkey_patch(socket=True)
        super(EventletConsumer, self).__init__(db)

    def _fetch(self, cb, **params):
        resp = self.db.res.get("_changes", **params)
        cb(resp.json_body)

    def fetch(self, cb=None, **params):
        if cb is None:
            return super(EventletConsumer, self).wait_once(**params)
        eventlet.spawn_n(self._fetch, cb, **params)

    def wait_once(self, cb=None, **params):
        if cb is None:
            return super(EventletConsumer, self).wait_once(**params)

        check_callable(cb)
        params.update({"feed": "longpoll"})
        consumer = LongPollChangeConsumer(self.db, callback=cb,
                **params)
        consumer.wait()

    def wait(self, cb, **params):
        params.update({"feed": "continuous"})
        consumer = ContinuousChangeConsumer(self.db, callback=cb,
                **params)
        consumer.wait()

    def wait_once_async(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "longpoll"})
        consumer = LongPollChangeConsumer(self.db, callback=cb,
                **params)
        return consumer.wait_async()

    def wait_async(self, cb, **params):
        check_callable(cb)
        params.update({"feed": "continuous"})
        consumer = ContinuousChangeConsumer(self.db, callback=cb,
                **params)
        return consumer.wait_async()

