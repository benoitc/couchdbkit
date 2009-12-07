# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import unittest

from restkit.errors import RequestFailed, RequestError
from couchdbkit.resource import CouchdbResource


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        try:
            self.couchdb.delete('/couchdkbit_test')
        except:
            pass
        
    def tearDown(self):
        self.couchdb = None
        try:
            self.couchdb.delete('/couchdkbit_test')
        except:
            pass

    def testGetInfo(self):
        info = self.couchdb.get().json_body
        self.assert_(info.has_key('version'))
        
    def testCreateDb(self):
        res = self.couchdb.put('/couchdkbit_test').json_body
        self.assert_(res['ok'] == True)
        all_dbs = self.couchdb.get('/_all_dbs').json_body
        self.assert_('couchdkbit_test' in all_dbs)
        self.couchdb.delete('/couchdkbit_test')

    def testCreateEmptyDoc(self):
        res = self.couchdb.put('/couchdkbit_test/').json_body
        self.assert_(res['ok'] == True)
        res = self.couchdb.post('/couchdkbit_test/', payload={}).json_body
        self.couchdb.delete('/couchdkbit_test')
        self.assert_(len(res) > 0)

    def testRequestFailed(self):
        bad = CouchdbResource('http://localhost:10000')
        self.assertRaises(RequestFailed, bad.get)
        
if __name__ == '__main__':
    unittest.main()


