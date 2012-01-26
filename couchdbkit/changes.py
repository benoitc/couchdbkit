# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.
#
# module to fetch and stream changes from a database
#

from .utils import json

class ChangesStream(object):
    """ change stream object::

        from couchdbkit import Server
        from couchdbkit.changes import ChangesStream

        s = Server()
        db = s['testdb']
        stream = ChangesStream(db)

        print "got change now"
        for c in stream:
            print c

        print "stream changes"
        with ChangesStream(db, feed="continuous", heartbeat=True) as stream:
            for c in stream:
                print c
    """


    def __init__(self, db, **params):
        self.db = db
        self.params = params

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __iter__(self):
        r = self.db.res.get("_changes", **self.params)
        with r.body_stream() as body:
            while True:
                line = body.readline()
                if not line:
                    break
                if line.endswith("\r\n"):
                    line = line[:-2]
                else:
                    line = line[:-1]
                if not line: # heartbeat
                    continue

                if line.endswith(","):
                    line = line[:-1]
                ret = self._parse_change(line)
                if not ret:
                    continue
                yield ret

    def _parse_change(self, line):
        if line.startswith('{"results":') or line.startswith('"last_seq'):
            return None
        else:
            try:
                obj = json.loads(line)
                return obj
            except ValueError, e:
                return None

    def __next__(self):
        return self


def fold(db, fun, acc, since=0):
    """ fold each changes and accuumulate result using a function

    Args:
        @param db: a database object
        @param fun: a callable with arity 2::

            fun(change_object, acc):
                return acc

            if acc == "stop": it will stop
        @param since: sequence wheer to start the feed

    @return: acc last acc returned
    """

    if not callable(fun):
        raise TypeError("fun isn't a callable")

    with ChangesStream(db, since=since) as st:
        for c in st:
            acc = fun(c, acc)
    return acc


def foreach(db, fun, since=0):
    """ iter each changes and pass it to the callable """
    if not callable(fun):
        raise TypeError("fun isn't a callable")

    with ChangesStream(db, since=since) as st:
        for c in st:
            fun(c)
