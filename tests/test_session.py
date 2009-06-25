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

from restclient import ResourceNotFound, RequestFailed

from couchdbkit import *

class SessionDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.Server = Server()
        self.db = self.Server.create_db('couchdbkit_test')
        self.session = create_session(self.Server, 'couchdbkit_test')

    def tearDown(self):
        del self.Server['couchdbkit_test']

    def testCreateDatabase(self):
        info = self.session.info()
        self.assert_(info['db_name'] == 'couchdbkit_test')

    def testCreateEmptyDoc(self):
        doc = {}
        self.session.save_doc(doc)
        self.assert_('_id' in doc)
        
        
    def testCreateDoc(self):
        # create doc without id
        doc = { 'string': 'test', 'number': 4 }
        self.session.save_doc(doc)
        self.assert_(self.session.doc_exist(doc['_id']))
        # create doc with id
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4 }
        self.session.save_doc(doc1)
        self.assert_(self.session.doc_exist('test'))
        doc2 = { 'string': 'test', 'number': 4 }
        self.session['test2'] = doc2
        self.assert_(self.session.doc_exist('test2'))

    def testUpdateDoc(self):
        doc = { 'string': 'test', 'number': 4 }
        self.session.save_doc(doc)
        doc.update({'number': 6})
        self.session.save_doc(doc)
        doc = self.session.get(doc['_id'])
        self.assert_(doc['number'] == 6)
        
    def testDocWithSlashes(self):
         doc = { '_id': "a/b"}
         self.session.save_doc(doc)
         self.assert_( "a/b" in self.session) 
         self.assert_( "a/b" in self.session)
         
         doc = { '_id': '_design/a' }
         self.session.save_doc(doc)
         self.assert_( "_design/a" in self.session)
        
    def testDbLen(self):
        doc1 = { 'string': 'test', 'number': 4 }
        self.session.save_doc(doc1)
        doc2 = { 'string': 'test2', 'number': 4 }
        self.session.save_doc(doc2)

        self.assert_(len(self.session) == 2)
        
    def testDeleteDoc(self):
        doc = { 'string': 'test', 'number': 4 }
        self.session.save_doc(doc)
        docid=doc['_id']
        self.session.delete_doc(docid)
        self.assert_(self.session.doc_exist(docid) == False)
        doc = { 'string': 'test', 'number': 4 }
        self.session.save_doc(doc)
        docid=doc['_id']
        self.session.delete_doc(doc)
        self.assert_(self.session.doc_exist(docid) == False)

    def testStatus404(self):
        def no_doc():
            doc = self.session.get('t')

        self.assertRaises(ResourceNotFound, no_doc)
        
    def testInlineAttachments(self):
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        doc = { 
            '_id': "docwithattachment", 
            "f": "value", 
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                }
            }
        }
        self.session.save_doc(doc)
        fetch_attachment = self.session.fetch_attachment(doc, "test.html")
        self.assert_(attachment == fetch_attachment)
        doc1 = self.session.get("docwithattachment")
        self.assert_('_attachments' in doc1)
        self.assert_('test.html' in doc1['_attachments'])
        self.assert_('stub' in doc1['_attachments']['test.html'])
        self.assert_(doc1['_attachments']['test.html']['stub'] == True)
        self.assert_(len(attachment) == doc1['_attachments']['test.html']['length'])
        
    def testMultipleInlineAttachments(self):
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        attachment2 = "<html><head><title>test attachment</title></head><body><p>More words</p></body></html>"
        doc = { 
            '_id': "docwithattachment", 
            "f": "value", 
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                },
                "test2.html": {
                    "type": "text/html",
                    "data": attachment2
                }
            }
        }
        
        self.session.save_doc(doc)
        fetch_attachment = self.session.fetch_attachment(doc, "test.html")
        self.assert_(attachment == fetch_attachment)
        fetch_attachment = self.session.fetch_attachment(doc, "test2.html")
        self.assert_(attachment2 == fetch_attachment)
        
        doc1 = self.session.get("docwithattachment")
        self.assert_('test.html' in doc1['_attachments'])
        self.assert_('test2.html' in doc1['_attachments'])
        self.assert_(len(attachment) == doc1['_attachments']['test.html']['length'])
        self.assert_(len(attachment2) == doc1['_attachments']['test2.html']['length'])
        
    def testInlineAttachmentWithStub(self):
        attachment = "<html><head><title>test attachment</title></head><body><p>Some words</p></body></html>"
        attachment2 = "<html><head><title>test attachment</title></head><body><p>More words</p></body></html>"
        doc = { 
            '_id': "docwithattachment", 
            "f": "value", 
            "_attachments": {
                "test.html": {
                    "type": "text/html",
                    "data": attachment
                }
            }
        }
        self.session.save_doc(doc)
        doc1 = self.session.get("docwithattachment")
        doc1["_attachments"].update({
            "test2.html": {
                "type": "text/html",
                "data": attachment2
            }
        })
        self.session.save_doc(doc1)
        
        fetch_attachment = self.session.fetch_attachment(doc1, "test2.html")
        self.assert_(attachment2 == fetch_attachment)
        
        doc2 = self.session.get("docwithattachment")
        self.assert_('test.html' in doc2['_attachments'])
        self.assert_('test2.html' in doc2['_attachments'])
        self.assert_(len(attachment) == doc2['_attachments']['test.html']['length'])
        self.assert_(len(attachment2) == doc2['_attachments']['test2.html']['length'])
        
    def testAttachments(self):
        doc = { 'string': 'test', 'number': 4 }
        self.session.save_doc(doc)        
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        self.session.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = self.session.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
   
    def testEmptyAttachment(self):
        doc = {}
        self.session.save_doc(doc)
        self.session.put_attachment(doc, "", name="test")
        doc1 = self.session.get(doc['_id'])
        attachment = doc1['_attachments']['test']
        self.assertEqual(0, attachment['length'])

    def testDeleteAttachment(self):
        doc = { 'string': 'test', 'number': 4 }
        self.session.save_doc(doc)
        
        text_attachment = "un texte attaché"
        old_rev = doc['_rev']
        self.session.put_attachment(doc, text_attachment, "test", "text/plain")
        self.session.delete_attachment(doc, 'test')
        attachment = self.session.fetch_attachment(doc, 'test')
        self.assert_(attachment == None)

    def testSaveMultipleDocs(self):
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        self.session.bulk_save(docs)
        self.assert_(len(self.session) == 4)
        self.assert_('_id' in docs[0])
        self.assert_('_rev' in docs[0])
        doc = self.session.get(docs[2]['_id'])
        self.assert_(doc['number'] == 4)
        docs[3]['number'] = 6
        old_rev = docs[3]['_rev']
        self.session.bulk_save(docs)
        self.assert_(docs[3]['_rev'] != old_rev)
        doc = self.session.get(docs[3]['_id'])
        self.assert_(doc['number'] == 6)
        docs = [
                { '_id': 'test', 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { '_id': 'test2', 'string': 'test', 'number': 42 },
                { 'string': 'test', 'number': 6 }
        ]
        self.session.bulk_save(docs)
        doc = self.session.get('test2')
        self.assert_(doc['number'] == 42)
   
    def testDeleteMultipleDocs(self):
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        self.session.bulk_save(docs)
        self.assert_(len(self.session) == 4)
        self.session.bulk_delete(docs)
        self.assert_(len(self.session) == 0)
        self.assert_(self.session.info()['doc_del_count'] == 4)
        
    def testCopy(self):
        doc = { "f": "a" }
        self.session.save_doc(doc)
        
        self.session.copy_doc(doc['_id'], "test")
        self.assert_("test" in self.session)
        doc1 = self.session.get("test")
        self.assert_('f' in doc1)
        self.assert_(doc1['f'] == "a")
        
        self.session.copy_doc(doc, "test2")
        self.assert_("test2" in self.session)
        
        doc2 = { "_id": "test3", "f": "c"}
        self.session.save_doc(doc2)
        
        self.session.copy_doc(doc, doc2)
        self.assert_("test3" in self.session)
        doc3 = self.session.get("test3")
        self.assert_(doc3['f'] == "a")
        
        doc4 = { "_id": "test5", "f": "c"}
        self.session.save_doc(doc4)
        self.session.copy_doc(doc, "test6")
        doc6 = self.session.get("test6")
        self.assert_(doc6['f'] == "a")
        
    def testDocumentWithSession(self):
        class A(Document):
            s = StringProperty(default='test')
            
        A = self.session(A)
        a = A()
        a.save()
    
        self.assert_(a._id in self.db)
        
    def testDocumentWithSession2(self):
        class A(Document):
            s = StringProperty(default='test')

        a = A()
        self.session(a).save()
        self.assert_(a._id in self.db)
        
    def testDocumentWithSession3(self):
        class A(Document):
            s = StringProperty(default='test')

        A.set_db(self.session)
        a = A()
        a.save()
        self.assert_(a._id in self.db)
        
    def testCustomDatabaseClass(self):
        class CustomDatabase(Database):
            def foo(self):
                return "foo"
                
        session = create_session(self.Server, 'couchdbkit_test',
                database_class=CustomDatabase)
                
        self.assert_(hasattr(session, 'foo') == True)
        self.assert_(session.foo() == "foo")
        
        
        