# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

def check_callable(cb):
    if not callable(cb):
        raise TypeError("callback isn't a callable")

class ConsumerBase(object):

    def __init__(self, db, **kwargs):
        self.db = db

    def fetch(self, cb=None, **params):
        resp = self.db.res.get("_changes", **params)
        if cb is not None:
            check_callable(cb)
            cb(resp.json_body)
        else:
            return resp.json_body

    def wait_once(self, cb=None, **params):
        raise NotImplementedError

    def wait(self, cb, **params):
        raise NotImplementedError
    
    def wait_once_async(self, cb, **params):
        raise NotImplementedError

    def wait_async(self, cb, **params):
        raise NotImplementedError
