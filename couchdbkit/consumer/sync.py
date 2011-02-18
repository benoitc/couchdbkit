# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

from .base import ConsumerBase, check_callable
from ..utils import json

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

        with resp.body_stream() as body:
            while True:
                try:
                    line = body.readline()
                    if not line:
                        break
                    if line.endswith("\r\n"):
                        line = line[:-2]
                    else:
                        line = line[:-1]
                    if not line:
                        continue

                    cb(json.loads(line))
                except (KeyboardInterrupt, SystemExit,):
                    break
