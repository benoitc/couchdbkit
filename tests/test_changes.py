# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import threading
import time
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from couchdbkit import *
from couchdbkit.changes import ChangesStream, fold, foreach

class ClientServerTestCase(unittest.TestCase):

    def setUp(self):
        self.server = Server()
        self._delete_db()
        self.db = self.server.create_db("couchdbkit_test")
        self.consumer = Consumer(self.db)

    def tearDown(self):
        self._delete_db()

    def _delete_db(self):
        try:
            del self.server['couchdbkit_test']
        except:
            pass


    def test_fetch(self):
        # save a doc
        doc = {}
        self.db.save_doc(doc)

        def fold_fun(c, acc):
            acc.append(c)
            return acc

        changes = fold(self.db, fold_fun, [])

        self.assert_(len(changes) == 1)
        change = changes[0]
        self.assert_(change["id"] == doc['_id'])


    def test_lonpoll(self):
        def test_change():
            with ChangesStream(self.db, feed="longpoll") as stream:
                for change in stream:
                    self.assert_(change["seq"] == 1)

        t = threading.Thread(target=test_change)
        t.daemon = True
        t.start()

        doc = {}
        self.db.save_doc(doc)


    def test_continuous(self):
        lines = []
        def test_change():
            with ChangesStream(self.db, feed="continuous") as stream:
                for change in stream:
                    lines.append(change)


        t = threading.Thread(target=test_change)
        t.daemon = True
        t.start()

        for i in range(5):
            doc = {"_id": "test%s" % str(i)}
            self.db.save_doc(doc)

        self.db.ensure_full_commit()
        time.sleep(0.3)
        self.assert_(len(lines) == 5)
        self.assert_(lines[4]["id"] == "test4")
        doc = {"_id": "test5"}
        self.db.save_doc(doc)
        time.sleep(0.3)
        self.assert_(len(lines) == 6)
        self.assert_(lines[5]["id"] == "test5")

