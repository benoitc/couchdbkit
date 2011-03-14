# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.
#
__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import copy
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from couchdbkit import ResourceNotFound, RequestFailed, \
ResourceConflict

from couchdbkit import *


class ClientServerTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()
        
    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
            del self.Server['couchdbkit/test']
        except:
            pass

    def testGetInfo(self):
        info = self.Server.info()
        self.assert_(info.has_key('version'))
        
    def testCreateDb(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_(isinstance(res, Database) == True)
        all_dbs = self.Server.all_dbs()
        self.assert_('couchdbkit_test' in all_dbs)
        del self.Server['couchdbkit_test']
        res = self.Server.create_db("couchdbkit/test")
        self.assert_('couchdbkit/test' in self.Server.all_dbs())
        del self.Server['couchdbkit/test']
        
    def testGetOrCreateDb(self):
        # create the database
        gocdb = self.Server.get_or_create_db("get_or_create_db")
        self.assert_(gocdb.dbname == "get_or_create_db")
        self.assert_("get_or_create_db" in self.Server)
        self.Server.delete_db("get_or_create_db")
        # get the database (already created)
        self.assertFalse("get_or_create_db" in self.Server)
        db = self.Server.create_db("get_or_create_db")
        self.assert_("get_or_create_db" in self.Server)
        gocdb = self.Server.get_or_create_db("get_or_create_db")
        self.assert_(db.dbname == gocdb.dbname)
        self.Server.delete_db("get_or_create_db")
        

    def testCreateInvalidDbName(self):

        def create_invalid():
            res = self.Server.create_db('123ab')

        self.assertRaises(ValueError, create_invalid) 
    
    def testServerLen(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_(len(self.Server) >= 1)
        self.assert_(bool(self.Server))
        del self.Server['couchdbkit_test']
        
    def testServerContain(self):
        res = self.Server.create_db('couchdbkit_test')
        self.assert_('couchdbkit_test' in self.Server)
        del self.Server['couchdbkit_test']
        
        
    def testGetUUIDS(self):
        uuid = self.Server.next_uuid()
        self.assert_(isinstance(uuid, basestring) == True)
        self.assert_(len(self.Server._uuids) == 999)
        uuid2 = self.Server.next_uuid()
        self.assert_(uuid != uuid2)
        self.assert_(len(self.Server._uuids) == 998)
        
class ClientDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()

    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
        except:
            pass
        
    def testCreateDatabase(self):
        db = self.Server.create_db('couchdbkit_test')
        self.assert_(isinstance(db, Database) == True)
        info = db.info()
        self.assert_(info['db_name'] == 'couchdbkit_test')
        del self.Server['couchdbkit_test']
        
    def testDbFromUri(self):
        db = self.Server.create_db('couchdbkit_test')
        
        db1 = Database("http://127.0.0.1:5984/couchdbkit_test")
        self.assert_(hasattr(db1, "dbname") == True)
        self.assert_(db1.dbname == "couchdbkit_test")
        info = db1.info()
        self.assert_(info['db_name'] == "couchdbkit_test")
        

    def testCreateEmptyDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        del self.Server['couchdbkit_test']
        self.assert_('_id' in doc)
        
        
    def testCreateDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        # create doc without id
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        self.assert_(db.doc_exist(doc['_id']))
        # create doc with id
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        self.assert_(db.doc_exist('test'))
        doc2 = { 'string': 'test', 'number': 4 }
        db['test2'] = doc2
        self.assert_(db.doc_exist('test2'))
        del self.Server['couchdbkit_test']
        
        db = self.Server.create_db('couchdbkit/test')
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        self.assert_(db.doc_exist('test'))
        del self.Server['couchdbkit/test']
            
    def testUpdateDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        doc.update({'number': 6})
        db.save_doc(doc)
        doc = db.get(doc['_id'])
        self.assert_(doc['number'] == 6)
        del self.Server['couchdbkit_test']
        
    def testDocWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': "a/b"}
        db.save_doc(doc)
        self.assert_( "a/b" in db) 
 
        doc = { '_id': "http://a"}
        db.save_doc(doc)
        self.assert_( "http://a" in db)
        doc = db.get("http://a")
        self.assert_(doc is not None)
 
        def not_found():
            doc = db.get('http:%2F%2Fa')
        self.assertRaises(ResourceNotFound, not_found)
 
        self.assert_(doc.get('_id') == "http://a")
        doc.get('_id')

        doc = { '_id': "http://b"}
        db.save_doc(doc)
        self.assert_( "http://b" in db)
 
        doc = { '_id': '_design/a' }
        db.save_doc(doc)
        self.assert_( "_design/a" in db)
        del self.Server['couchdbkit_test']
        
    def testGetRev(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        rev = db.get_rev(doc['_id'])
        self.assert_(rev == doc['_rev'])
        
    def testForceUpdate(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        doc1 = doc.copy()
        db.save_doc(doc)
        self.assertRaises(ResourceConflict, db.save_doc, doc1)
        
        is_conflict = False
        try:
            db.save_doc(doc1, force_update=True)
        except ResourceConflict:
            is_conflict = True

        self.assert_(is_conflict == False)
        
    
    def testMultipleDocWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': "a/b"}
        doc1 = { '_id': "http://a"}
        doc3 = { '_id': '_design/a' }
        db.bulk_save([doc, doc1, doc3])
        self.assert_( "a/b" in db) 
        self.assert_( "http://a" in db)
        self.assert_( "_design/a" in db)

        def not_found():
            doc = db.get('http:%2F%2Fa')
        self.assertRaises(ResourceNotFound, not_found)

    def testFlush(self):
        db = self.Server.create_db('couchdbkit_test')
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        doc2 = { 'string': 'test', 'number': 4 }
        db['test2'] = doc2
        self.assert_(db.doc_exist('test'))
        self.assert_(db.doc_exist('test2'))
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
            }}"""
                }
            }
        }
        db.save_doc(design_doc)
        self.assert_(len(db) == 3)
        db.flush()
        self.assert_(len(db) == 1)
        self.assertFalse(db.doc_exist('test'))
        self.assertFalse(db.doc_exist('test2'))
        self.assert_(db.doc_exist('_design/test'))
        ddoc = db.get("_design/test")
        self.assert_('all' in ddoc['views'])
        del self.Server['couchdbkit_test']
    
    def testDbLen(self):
        db = self.Server.create_db('couchdbkit_test')
        doc1 = { 'string': 'test', 'number': 4 }
        db.save_doc(doc1)
        doc2 = { 'string': 'test2', 'number': 4 }
        db.save_doc(doc2)

        self.assert_(len(db) == 2)
        del self.Server['couchdbkit_test']
        
    def testDeleteDoc(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        docid=doc['_id']
        db.delete_doc(docid)
        self.assert_(db.doc_exist(docid) == False)
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        docid=doc['_id']
        db.delete_doc(doc)
        self.assert_(db.doc_exist(docid) == False)
        
        del self.Server['couchdbkit_test']

    def testStatus404(self):
        db = self.Server.create_db('couchdbkit_test')

        def no_doc():
            doc = db.get('t')

        self.assertRaises(ResourceNotFound, no_doc)
        
        del self.Server['couchdbkit_test']
        
    def testInlineAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
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
        db.save_doc(doc)
        fetch_attachment = db.fetch_attachment(doc, "test.html")
        self.assert_(attachment == fetch_attachment)
        doc1 = db.get("docwithattachment")
        self.assert_('_attachments' in doc1)
        self.assert_('test.html' in doc1['_attachments'])
        self.assert_('stub' in doc1['_attachments']['test.html'])
        self.assert_(doc1['_attachments']['test.html']['stub'] == True)
        self.assert_(len(attachment) == doc1['_attachments']['test.html']['length'])
        del self.Server['couchdbkit_test']
    
    def testMultipleInlineAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
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
        
        db.save_doc(doc)
        fetch_attachment = db.fetch_attachment(doc, "test.html")
        self.assert_(attachment == fetch_attachment)
        fetch_attachment = db.fetch_attachment(doc, "test2.html")
        self.assert_(attachment2 == fetch_attachment)
        
        doc1 = db.get("docwithattachment")
        self.assert_('test.html' in doc1['_attachments'])
        self.assert_('test2.html' in doc1['_attachments'])
        self.assert_(len(attachment) == doc1['_attachments']['test.html']['length'])
        self.assert_(len(attachment2) == doc1['_attachments']['test2.html']['length'])
        del self.Server['couchdbkit_test']
        
    def testInlineAttachmentWithStub(self):
        db = self.Server.create_db('couchdbkit_test')
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
        db.save_doc(doc)
        doc1 = db.get("docwithattachment")
        doc1["_attachments"].update({
            "test2.html": {
                "type": "text/html",
                "data": attachment2
            }
        })
        db.save_doc(doc1)
        
        fetch_attachment = db.fetch_attachment(doc1, "test2.html")
        self.assert_(attachment2 == fetch_attachment)
        
        doc2 = db.get("docwithattachment")
        self.assert_('test.html' in doc2['_attachments'])
        self.assert_('test2.html' in doc2['_attachments'])
        self.assert_(len(attachment) == doc2['_attachments']['test.html']['length'])
        self.assert_(len(attachment2) == doc2['_attachments']['test2.html']['length'])
        del self.Server['couchdbkit_test']
        
    def testAttachments(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)        
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
        del self.Server['couchdbkit_test']
        
    def testFetchAttachmentStream(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)        
        text_attachment = u"a text attachment"
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        stream = db.fetch_attachment(doc, "test", stream=True)
        fetch_attachment = stream.read()
        self.assert_(text_attachment == fetch_attachment)
        del self.Server['couchdbkit_test']
   
    def testEmptyAttachment(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = {}
        db.save_doc(doc)
        db.put_attachment(doc, "", name="test")
        doc1 = db.get(doc['_id'])
        attachment = doc1['_attachments']['test']
        self.assertEqual(0, attachment['length'])
        del self.Server['couchdbkit_test']

    def testDeleteAttachment(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { 'string': 'test', 'number': 4 }
        db.save_doc(doc)
        
        text_attachment = "un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        db.delete_attachment(doc, 'test')
        self.assertRaises(ResourceNotFound, db.fetch_attachment, doc, 'test')
        del self.Server['couchdbkit_test']
        
    def testAttachmentsWithSlashes(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': 'test/slashes', 'string': 'test', 'number': 4 }
        db.save_doc(doc)        
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
        
        db.put_attachment(doc, text_attachment, "test/test.txt", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test/test.txt")
        self.assert_(text_attachment == fetch_attachment)
        
        del self.Server['couchdbkit_test']
        
        
    def testAttachmentUnicode8URI(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { '_id': u"éàù/slashes", 'string': 'test', 'number': 4 }
        db.save_doc(doc)        
        text_attachment = u"un texte attaché"
        old_rev = doc['_rev']
        db.put_attachment(doc, text_attachment, "test", "text/plain")
        self.assert_(old_rev != doc['_rev'])
        fetch_attachment = db.fetch_attachment(doc, "test")
        self.assert_(text_attachment == fetch_attachment)
        del self.Server['couchdbkit_test']
        
    def testSaveMultipleDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        self.assert_(len(db) == 4)
        self.assert_('_id' in docs[0])
        self.assert_('_rev' in docs[0])
        doc = db.get(docs[2]['_id'])
        self.assert_(doc['number'] == 4)
        docs[3]['number'] = 6
        old_rev = docs[3]['_rev']
        db.bulk_save(docs)
        self.assert_(docs[3]['_rev'] != old_rev)
        doc = db.get(docs[3]['_id'])
        self.assert_(doc['number'] == 6)
        docs = [
                { '_id': 'test', 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { '_id': 'test2', 'string': 'test', 'number': 42 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        doc = db.get('test2')
        self.assert_(doc['number'] == 42) 
        del self.Server['couchdbkit_test']
   
    def testDeleteMultipleDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        self.assert_(len(db) == 4)
        db.bulk_delete(docs)
        self.assert_(len(db) == 0)
        self.assert_(db.info()['doc_del_count'] == 4)

        del self.Server['couchdbkit_test']
        
    def testMultipleDocCOnflict(self):
        db = self.Server.create_db('couchdbkit_test')
        docs = [
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 5 },
                { 'string': 'test', 'number': 4 },
                { 'string': 'test', 'number': 6 }
        ]
        db.bulk_save(docs)
        self.assert_(len(db) == 4)
        docs1 = [
                docs[0],
                docs[1],
                {'_id': docs[2]['_id'], 'string': 'test', 'number': 4 },
                {'_id': docs[3]['_id'], 'string': 'test', 'number': 6 }
        ]

        self.assertRaises(BulkSaveError, db.bulk_save, docs1)

        docs2 = [
            docs1[0],
            docs1[1],
            {'_id': docs[2]['_id'], 'string': 'test', 'number': 4 },
            {'_id': docs[3]['_id'], 'string': 'test', 'number': 6 }
        ]
        doc23 = docs2[3].copy()
        all_errors = []
        try:
            db.bulk_save(docs2)
        except BulkSaveError, e:
            all_errors = e.errors

        self.assert_(len(all_errors) == 2)
        self.assert_(all_errors[0]['error'] == 'conflict')
        self.assert_(doc23 == docs2[3])
        
        docs3 = [
            docs2[0],
            docs2[1],
            {'_id': docs[2]['_id'], 'string': 'test', 'number': 4 },
            {'_id': docs[3]['_id'], 'string': 'test', 'number': 6 }
        ]
        
        doc33 = docs3[3].copy()
        all_errors2 = []
        try:
            db.bulk_save(docs3, all_or_nothing=True)
        except BulkSaveError, e:
            all_errors2 = e.errors
        
        self.assert_(len(all_errors2) == 0)
        self.assert_(doc33 != docs3[3])
        del self.Server['couchdbkit_test']


    def testCopy(self):
        db = self.Server.create_db('couchdbkit_test')
        doc = { "f": "a" }
        db.save_doc(doc)
        
        db.copy_doc(doc['_id'], "test")
        self.assert_("test" in db)
        doc1 = db.get("test")
        self.assert_('f' in doc1)
        self.assert_(doc1['f'] == "a")
        
        db.copy_doc(doc, "test2")
        self.assert_("test2" in db)
        
        doc2 = { "_id": "test3", "f": "c"}
        db.save_doc(doc2)
        
        db.copy_doc(doc, doc2)
        self.assert_("test3" in db)
        doc3 = db.get("test3")
        self.assert_(doc3['f'] == "a")
        
        doc4 = { "_id": "test5", "f": "c"}
        db.save_doc(doc4)
        db.copy_doc(doc, "test6")
        doc6 = db.get("test6")
        self.assert_(doc6['f'] == "a")
        
        del self.Server['couchdbkit_test']


class ClientViewTestCase(unittest.TestCase):
    def setUp(self):
        self.couchdb = CouchdbResource()
        self.Server = Server()

    def tearDown(self):
        try:
            del self.Server['couchdbkit_test']
        except:
            pass

        try:
            self.Server.delete_db('couchdbkit_test2')
        except:
            pass

    def testView(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
                }
            }
        }
        db.save_doc(design_doc)
        
        doc3 = db.get('_design/test')
        self.assert_(doc3 is not None) 
        results = db.view('test/all')
        self.assert_(len(results) == 2)
        del self.Server['couchdbkit_test']

    def testAllDocs(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)
        
        self.assert_(db.view('_all_docs').count() == 2 )
        self.assert_(db.view('_all_docs').all() == db.all_docs().all())

        del self.Server['couchdbkit_test']

    def testCount(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc); }}"""
                }
            }
        }
        db.save_doc(design_doc)
        count = db.view('/test/all').count()
        self.assert_(count == 2)
        del self.Server['couchdbkit_test']

    def testTemporaryView(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)

        design_doc = {
            "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
        }
         
        results = db.temp_view(design_doc)
        self.assert_(len(results) == 2)
        del self.Server['couchdbkit_test']


    def testView2(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test1', 'string': 'test', 'number': 4, 
                'docType': 'test' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                    'docType': 'test'}
        db.save_doc(doc2)
        doc3 = { '_id': 'test3', 'string': 'test', 'number': 2,
                    'docType': 'test2'}
        db.save_doc(doc3)
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'with_test': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc._id, doc);
}}"""
                },
                'with_test2': {
                    "map": """function(doc) { if (doc.docType == "test2") { emit(doc._id, doc);
}}"""
                }   

            }
        }
        db.save_doc(design_doc)

        # yo view is callable !
        results = db.view('test/with_test')
        self.assert_(len(results) == 2)
        results = db.view('test/with_test2')
        self.assert_(len(results) == 1)
        del self.Server['couchdbkit_test']

    def testViewWithParams(self):
        db = self.Server.create_db('couchdbkit_test')
        # save 2 docs 
        doc1 = { '_id': 'test1', 'string': 'test', 'number': 4, 
                'docType': 'test', 'date': '20081107' }
        db.save_doc(doc1)
        doc2 = { '_id': 'test2', 'string': 'test', 'number': 2,
                'docType': 'test', 'date': '20081107'}
        db.save_doc(doc2)
        doc3 = { '_id': 'test3', 'string': 'machin', 'number': 2,
                    'docType': 'test', 'date': '20081007'}
        db.save_doc(doc3)
        doc4 = { '_id': 'test4', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081108'}
        db.save_doc(doc4)
        doc5 = { '_id': 'test5', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081109'}
        db.save_doc(doc5)
        doc6 = { '_id': 'test6', 'string': 'test2', 'number': 2,
                'docType': 'test', 'date': '20081109'}
        db.save_doc(doc6)

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'test1': {
                    "map": """function(doc) { if (doc.docType == "test")
                    { emit(doc.string, doc);
}}"""
                },
                'test2': {
                    "map": """function(doc) { if (doc.docType == "test") { emit(doc.date, doc);
}}"""
                },
                'test3': {
                    "map": """function(doc) { if (doc.docType == "test")
                    { emit(doc.string, doc);
}}"""
                }


            }
        }
        db.save_doc(design_doc)

        results = db.view('test/test1')
        self.assert_(len(results) == 6)

        results = db.view('test/test3', key="test")
        self.assert_(len(results) == 2)

       

        results = db.view('test/test3', key="test2")
        self.assert_(len(results) == 3)

        results = db.view('test/test2', startkey="200811")
        self.assert_(len(results) == 5)

        results = db.view('test/test2', startkey="20081107",
                endkey="20081108")
        self.assert_(len(results) == 3)

        results = db.view('test/test1', keys=['test', 'machin'] )
        self.assert_(len(results) == 3)

        del self.Server['couchdbkit_test']

        
    def testMultiWrap(self):
        """
        Tests wrapping of view results to multiple
        classes using the client
        """

        class A(Document):
            pass
        class B(Document):
            pass

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { emit(doc._id, doc); }"""
                }
            }
        }
        a = A()
        a._id = "1"
        b = B()
        b._id = "2"
        db = self.Server.create_db('couchdbkit_test')
        A._db = db
        B._db = db

        a.save()
        b.save()
        db.save_doc(design_doc)
        # provide classes as a list
        results = list(db.view('test/all', schema=[A, B]))
        self.assert_(results[0].__class__ == A)
        self.assert_(results[1].__class__ == B)
        # provide classes as a dict
        results = list(db.view('test/all', schema={'A': A, 'B': B}))
        self.assert_(results[0].__class__ == A)
        self.assert_(results[1].__class__ == B)
        self.Server.delete_db('couchdbkit_test')


if __name__ == '__main__':
    unittest.main()

