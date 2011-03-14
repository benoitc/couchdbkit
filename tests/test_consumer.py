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
        res1 = self.consumer.fetch()
        self.assert_("last_seq" in res1)
        self.assert_(res1["last_seq"] == 0)
        self.assert_(res1["results"] == [])
        doc = {}
        self.db.save_doc(doc)
        res2 = self.consumer.fetch()
        self.assert_(res2["last_seq"] == 1)
        self.assert_(len(res2["results"]) == 1)
        line = res2["results"][0]
        self.assert_(line["id"] == doc["_id"])    
        
    def test_longpoll(self):
        
        def test_line(line):
            self.assert_(line["last_seq"] == 1)
            self.assert_(len(line["results"]) == 1)
            return
            
        t =  threading.Thread(target=self.consumer.wait_once,
                kwargs=dict(cb=test_line))
        t.daemon = True
        t.start()
        doc = {}
        self.db.save_doc(doc)

    def test_continuous(self):
        self.lines = []
        def test_line(line):
            self.lines.append(line)
            
        t =  threading.Thread(target=self.consumer.wait,
                kwargs=dict(cb=test_line))
        t.daemon = True
        t.start()
        
        for i in range(5):
            doc = {"_id": "test%s" % str(i)}
            self.db.save_doc(doc)
        self.db.ensure_full_commit()
        time.sleep(0.5)
        self.assert_(len(self.lines) == 5)
        self.assert_(self.lines[4]["id"] == "test4")
        doc = {"_id": "test5"}
        self.db.save_doc(doc)
        time.sleep(0.5)
        self.assert_(len(self.lines) == 6)
        self.assert_(self.lines[5]["id"] == "test5")

        
if __name__ == '__main__':
    unittest.main()
