# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

__author__ = 'benoitc@e-engura.com (Benoît Chesneau)'

import datetime
import decimal
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from couchdbkit import *



class DocumentTestCase(unittest.TestCase):
    def setUp(self):
        self.server = Server()

    def tearDown(self):
        try:
            self.server.delete_db('couchdbkit_test')
        except:
            pass

        try:
            self.server.delete_db('couchdbkit_test2')
        except:
            pass

    def testStaticDocumentCreation(self):
        db = self.server.create_db('couchdbkit_test')

        # with _allow_dynamic_properties
        class Test(Document):
            _allow_dynamic_properties = False
            foo = StringProperty()
        Test._db = db

        doc = Test()
        doc.foo="test"
        try:
            doc.bar="bla"
        except AttributeError, e:
            self.assert_(str(e) == "bar is not defined in schema (not a valid property)")
        doc.save()
        self.assert_(not hasattr(doc, "bar"))
        assert doc._doc['foo'] == "test"

        # With StaticDocument
        class Test(StaticDocument):
            foo = StringProperty()
        Test._db = db

        doc = Test()
        doc.foo="test"
        try:
            doc.bar="bla"
        except AttributeError, e:
            self.assert_(str(e) == "bar is not defined in schema (not a valid property)")
        doc.save()
        self.assert_(not hasattr(doc, "bar"))
        self.assert_(doc._doc['foo'] == "test")

        doc1 = Test(foo="doc1")
        db.save_doc(doc1)
        self.assert_(doc1._doc['foo'] == "doc1")

        self.server.delete_db('couchdbkit_test')


    def testDynamicDocumentCreation(self):
        class Test(Document):
            pass

        class Test2(Document):
            string = StringProperty(default="test")


        doc = Test(string="essai")
        self.assert_(getattr(doc, 'string') is not None)
        self.assert_(doc.string == "essai")

        doc1 = Test(string="essai", string2="essai2")
        self.assert_(doc1.string == "essai")
        self.assert_(doc1.string2 == "essai2")

        doc2 = Test2(string2="essai")
        self.assert_(doc2.string == "test")

    def testDeleteProperty(self):
        class Test(Document):
            string = StringProperty(default="test")

        doc = Test(string="test")
        del doc.string
        self.assert_(getattr(doc, "string") == None)
        self.assert_(doc['string'] == None)

        class Test2(Document):
            pass

        doc1 = Test2(string="test")
        del doc1.string
        self.assert_(getattr(doc, "string") == None)
 

    def testContain(self):
        class Test(Document):
            string = StringProperty(default="test")
        doc = Test()
        self.assert_('string' in doc)
        self.assert_('test' not in doc)

        doc.test = "test"
        self.assert_('test' in doc)

    def testLen(self):
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()

        doc = Test()
        self.assert_(len(doc) == 3)
        doc.string3 = "4"
        self.assert_(len(doc) == 4) 
        
    def testStore(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()
        Test._db = db

        doc = Test()
        doc.string2 = "test2"

        doc.save()
        self.assert_(doc._id is not None)
        doc1 = db.get(doc._id)
        self.assert_(doc1['string2'] == "test2")

        doc2 = Test(string3="test")
        doc2.save()
        doc3 = db.get(doc2._id)
        self.assert_(doc3['string3'] == "test")

        doc4 = Test(string="doc4")
        db.save_doc(doc4)
        self.assert_(doc4._id is not None)

        self.server.delete_db('couchdbkit_test')

    def testBulkSave(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty()
        #Test._db = db
        class Test2(Document):
            string = StringProperty()

        doc1 = Test(string="test")
        self.assert_(doc1._id is None)
        doc2 = Test(string="test2")
        self.assert_(doc2._id is None)
        doc3 = Test(string="test3")
        self.assert_(doc3._id is None)

        try:
            Test.bulk_save( [doc1, doc2, doc3] )
        except TypeError, e:
            self.assert_(str(e)== "doc database required to save document" )

        Test.set_db( db )
        bad_doc = Test2(string="bad_doc")
        try:
            Test.bulk_save( [doc1, doc2, doc3, bad_doc] )
        except ValueError, e:
            self.assert_(str(e) == "one of your documents does not have the correct type" )

        Test.bulk_save( [doc1, doc2, doc3] )
        self.assert_(doc1._id is not None)
        self.assert_(doc1._rev is not None)
        self.assert_(doc2._id is not None)
        self.assert_(doc2._rev is not None)
        self.assert_(doc3._id is not None)
        self.assert_(doc3._rev is not None)
        self.assert_(doc1.string == "test")
        self.assert_(doc2.string == "test2")
        self.assert_(doc3.string == "test3")

        doc4 = Test(string="doc4")
        doc5 = Test(string="doc5")
        db.save_docs([doc4, doc5])
        self.assert_(doc4._id is not None)
        self.assert_(doc4._rev is not None)
        self.assert_(doc5._id is not None)
        self.assert_(doc5._rev is not None)
        self.assert_(doc4.string == "doc4")
        self.assert_(doc5.string == "doc5")
    
        self.server.delete_db('couchdbkit_test')

 

    def testGet(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty(default="test")
            string2 = StringProperty()
        Test._db = db

        doc = Test()
        doc.string2 = "test2"
        doc.save()
        doc2 = Test.get(doc._id)

        self.assert_(doc2.string2 == "test2")
    
        doc2.string3 = "blah"
        doc2.save()
        doc3 = db.get(doc2._id)
        self.assert_(doc3['string3'] == "blah")

        doc4 = db.open_doc(doc2._id, schema=Test)
        self.assert_(isinstance(doc4, Test) == True)
        self.assert_(doc4.string3 == "blah")

        self.server.delete_db('couchdbkit_test')

    def testLoadDynamicProperties(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            pass
        Test._db = db

        doc = Test(field="test",
                field1=datetime.datetime(2008, 11, 10, 8, 0, 0),
                field2=datetime.date(2008, 11, 10),
                field3=datetime.time(8, 0, 0),
                field4=decimal.Decimal("45.4"),
                field5=4.4)
        doc.save()
        doc1 = Test.get(doc._id)
        self.server.delete_db('couchdbkit_test')

        self.assert_(isinstance(doc1.field, basestring))
        self.assert_(isinstance(doc1.field1, datetime.datetime))
        self.assert_(isinstance(doc1.field2, datetime.date))
        self.assert_(isinstance(doc1.field3, datetime.time))
        self.assert_(isinstance(doc1.field4, decimal.Decimal))
        self.assert_(isinstance(doc1.field5, float))

    def testDocType(self):
        class Test(Document):
            string = StringProperty(default="test")
        
        class Test2(Document):
            string = StringProperty(default="test")
            
        class Test3(Document):
            doc_type = "test_type"
            string = StringProperty(default="test")

        doc1 = Test() 
        doc2 = Test2()
        doc3 = Test2()
        doc4 = Test3()

        self.assert_(doc1._doc_type == 'Test')
        self.assert_(doc1._doc['doc_type'] == 'Test')
        
        self.assert_(doc3._doc_type == 'Test2')
        self.assert_(doc4._doc_type == 'test_type')
        self.assert_(doc4._doc['doc_type'] == 'test_type')
        
        
        db = self.server.create_db('couchdbkit_test')
        Test3._db = Test2._db = Test._db = db

        doc1.save()
        doc2.save()
        doc3.save()
        doc4.save()
     
        get1 = Test.get(doc1._id)
        get2 = Test2.get(doc2._id)
        get3 = Test2.get(doc3._id)
        get4 = Test3.get(doc4._id)


        self.server.delete_db('couchdbkit_test')
        self.assert_(get1._doc['doc_type'] == 'Test')
        self.assert_(get2._doc['doc_type']== 'Test2')
        self.assert_(get3._doc['doc_type'] == 'Test2')
        self.assert_(get4._doc['doc_type'] == 'test_type')
        
    def testInheriting(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        class TestDoc2(TestDoc):
            field3 = StringProperty()
           
        doc = TestDoc2(field1="a", field2="b",
                field3="c")
        doc2 = TestDoc2(field1="a", field2="b",
                field3="c", field4="d")

        self.assert_(len(doc2._dynamic_properties) == 1)

    def testClone(self):
        class A(DocumentSchema):
            s = StringProperty()

        class B(Document):
            a = SchemaProperty(A)
            s1 = StringProperty()

        b = B()
        b.s1 = "test1"
        b.a.s = "test"
        b1 = b.clone()

        self.assert_(b1.s1 == "test1")
        self.assert_('s' in b1._doc['a'])
        self.assert_(b1.a.s == "test")

    def testView(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        doc3 = list(results)[0]
        self.assert_(hasattr(doc3, "field1"))
        self.server.delete_db('couchdbkit_test')

    def testMultiWrap(self):
        """
        Tests wrapping of view results to multiple
        classes using a Document class' wrap method
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

        db = self.server.create_db('couchdbkit_test')
        A._db = db
        B._db = db

        a.save()
        b.save()
        db.save_doc(design_doc)
        # provide classes as a list
        results = list(A.view('test/all', classes=[A, B]))
        self.assert_(results[0].__class__ == A)
        self.assert_(results[1].__class__ == B)
        # provide classes as a dict
        results = list(A.view('test/all', classes={'A': A, 'B': B}))
        self.assert_(results[0].__class__ == A)
        self.assert_(results[1].__class__ == B)
        self.server.delete_db('couchdbkit_test')
    
    def testViewNoneValue(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, null);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db
        
        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        self.assert_(isinstance(results.first(), dict) == True)
        results2 = TestDoc.view('test/all', include_docs=True)
        self.assert_(len(results2) == 2)
        self.assert_(isinstance(results2.first(), TestDoc) == True)       
        self.server.delete_db('couchdbkit_test')
        
        
    def testOne(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()

        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

       
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 0)
        self.assertRaises(NoResultFound, results.one, except_all=True)
        rst = results.one()
        self.assert_(rst is None)
        
        
        results = TestDoc.view('test/all')
        doc.save()
        self.assert_(len(results) == 1)
        
        one = results.one()
        self.assert_(isinstance(one, TestDoc) == True)
        
        doc1.save()
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        
        self.assertRaises(MultipleResultsFound, results.one)

        self.server.delete_db('couchdbkit_test')
        
    def testViewStringValue(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()
        
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc.field1);}}"""
                }
            }
        }
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")
        
        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db

        doc.save()
        doc1.save()
        db.save_doc(design_doc)
        results = TestDoc.view('test/all')
        self.assert_(len(results) == 2)
        self.server.delete_db('couchdbkit_test')
        

    def testTempView(self):
        class TestDoc(Document):
            field1 = StringProperty()
            field2 = StringProperty()
        
        design_doc = {
            "map": """function(doc) { if (doc.doc_type == "TestDoc") { emit(doc._id, doc);
}}"""
        }
       
        doc = TestDoc(field1="a", field2="b")
        doc1 = TestDoc(field1="c", field2="d")

        db = self.server.create_db('couchdbkit_test')
        TestDoc._db = db
        
        doc.save()
        doc1.save()
        results = TestDoc.temp_view(design_doc)
        self.assert_(len(results) == 2)
        doc3 = list(results)[0]
        self.assert_(hasattr(doc3, "field1"))
        self.server.delete_db('couchdbkit_test')
    
    def testDocumentAttachments(self):
        db = self.server.create_db('couchdbkit_test')
        
        class A(Document):
            s = StringProperty(default='test')
            i = IntegerProperty(default=4)
        A._db = db

        a = A()
        a.save()
  
        text_attachment = u"un texte attaché"
        old_rev = a._rev

        a.put_attachment(text_attachment, "test", "text/plain")
        self.assert_(old_rev != a._rev)
        fetch_attachment = a.fetch_attachment("test")
        self.assert_(text_attachment == fetch_attachment)
        self.server.delete_db('couchdbkit_test')
   

    def testDocumentDeleteAttachment(self):
        db = self.server.create_db('couchdbkit_test')
        class A(Document):
            s = StringProperty(default='test')
            i = IntegerProperty(default=4)
        A._db = db

        a = A()
        a.save()
        
        text_attachment = "un texte attaché"
        
        a.put_attachment(text_attachment, "test", "text/plain")
        a.delete_attachment('test')
        self.assertRaises(ResourceNotFound, a.fetch_attachment, 'test')
        self.assertFalse('test' in a._doc['_attachments'])
        
        self.server.delete_db('couchdbkit_test')

    def testGetOrCreate(self):
        self.server.create_db('couchdbkit_test')
        db = self.server['couchdbkit_test']

        class A(Document):
            s = StringProperty()
        A._db = db

        def no_exist():
            a = A.get('test')

        self.assertRaises(ResourceNotFound, no_exist)

        a = A.get_or_create('test')
        self.assert_(a._id == "test")
        
        b = A.get_or_create()
        self.assert_(a._id is not None)
        self.server.delete_db('couchdbkit_test')
    
    def testBulkDelete(self):
        db = self.server.create_db('couchdbkit_test')
        class Test(Document):
            string = StringProperty()

        doc1 = Test(string="test")
        doc2 = Test(string="test2")
        doc3 = Test(string="test3")

        Test.set_db(db)
        Test.bulk_save([doc1, doc2, doc3])

        db.bulk_delete([doc1, doc2, doc3])

        print list(db.all_docs(include_docs=True))
        self.assert_(len(db) == 0)
        self.assert_(db.info()['doc_del_count'] == 3)

        self.server.delete_db('couchdbkit_test')


class PropertyTestCase(unittest.TestCase):

    def setUp(self):
        self.server = Server()
        try:
            self.db = self.server.create_db('couchdbkit_test')
        except: 
            # waiting we fix all tests use created db
            self.db = self.server['couchdbkit_test']
            
    def tearDown(self):
        try:
            self.server.delete_db('couchdbkit_test')
        except:
            pass

    def testRequired(self):
        class Test(Document):
            string = StringProperty(required=True)
        Test._db = self.db

        test = Test()
        def ftest():
            test.string = ""
        self.assertRaises(BadValueError, test.save)

    def testRequiredBoolean(self):
        class Test(Document):
            boolean = BooleanProperty(required=True)
        Test._db = self.db

        test = Test()
        test.boolean = False
        test.save()

    def testValidator(self):
        def test_validator(value):
            if value == "test":
                raise BadValueError("test")

        class Test(Document):
            string = StringProperty(validators=test_validator)

        test = Test()
        def ftest():
            test.string = "test"
        self.assertRaises(BadValueError, ftest)

    def testIntegerProperty(self):
        class Test(Document):
            field = IntegerProperty()
        
        test = Test()
        def ftest():
            test.field = "essai" 
        
        
        self.assertRaises(BadValueError, ftest)
        test.field = 4
        self.assert_(test._doc['field'] == 4)

    def testDateTimeProperty(self):
        class Test(Document):
            field = DateTimeProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test_dates = [
            ([2008, 11, 10, 8, 0, 0], "2008-11-10T08:00:00Z"),
            ([9999, 12, 31, 23, 59, 59], '9999-12-31T23:59:59Z'),
            ([0001, 1, 1, 0, 0, 1], '0001-01-01T00:00:01Z'),

        ]
        for date, date_str in test_dates:
            test.field = datetime.datetime(*date)
            self.assertEquals(test._doc['field'], date_str)
            value = test.field
            self.assert_(isinstance(value, datetime.datetime))


        
    def testDateProperty(self):
        class Test(Document):
            field = DateProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test.field = datetime.date(2008, 11, 10)
        self.assert_(test._doc['field'] == "2008-11-10")
        value = test.field
        self.assert_(isinstance(value, datetime.date))


    def testTimeProperty(self):
        class Test(Document):
            field = TimeProperty()

        test = Test()
        def ftest():
            test.field = "essai"

        self.assertRaises(BadValueError, ftest)
        test.field = datetime.time(8, 0, 0)
        self.assert_(test._doc['field'] == "08:00:00")
        value = test.field
        self.assert_(isinstance(value, datetime.time))

    def testMixProperties(self):
        class Test(Document):
            field = StringProperty()
            field1 = DateTimeProperty()

        test = Test(field="test", 
                field1 = datetime.datetime(2008, 11, 10, 8, 0, 0))

        self.assert_(test._doc['field'] == "test")
        self.assert_(test._doc['field1'] == "2008-11-10T08:00:00Z")
       
        self.assert_(isinstance(test.field, basestring))
        self.assert_(isinstance(test.field1, datetime.datetime))
        Test._db = self.db
        test.save()
        doc2 = Test.get(test._id)
        
        v = doc2.field
        v1 = doc2.field1
        self.assert_(isinstance(v, basestring))
        self.assert_(isinstance(v1, datetime.datetime))
    
    def testMixDynamicProperties(self):
        class Test(Document):
            field = StringProperty()
            field1 = DateTimeProperty()

        test = Test(field="test", 
                field1 = datetime.datetime(2008, 11, 10, 8, 0, 0),
                dynamic_field = 'test')

        Test._db = self.db

        test.save()

        doc2 = Test.get(test._id)

        v1 = doc2.field1
        vd = doc2.dynamic_field

        self.assert_(isinstance(v1, datetime.datetime))
        self.assert_(isinstance(vd, basestring))


    def testSchemaProperty1(self):
        class MySchema(DocumentSchema):
            astring = StringProperty()

        class MyDoc(Document):
            schema = SchemaProperty(MySchema)

        doc = MyDoc()
        self.assert_('schema' in doc._doc)
        
        doc.schema.astring = u"test"
        self.assert_(doc.schema.astring == u"test")
        self.assert_(doc._doc['schema']['astring'] == u"test")
        
        MyDoc._db = self.db

        doc.save()
        doc2 = MyDoc.get(doc._id)
        
        self.assert_(isinstance(doc2.schema, MySchema) == True)
        self.assert_(doc2.schema.astring == u"test")
        self.assert_(doc2._doc['schema']['astring'] == u"test")


    def testSchemaPropertyWithRequired(self):
        class B( Document ):
            class b_schema(DocumentSchema):
                name = StringProperty(  required = True, default = "name" )
            b = SchemaProperty( b_schema )
            
        B._db = self.db
        
        b = B()
        self.assertEquals(b.b.name, "name" )

        def bad_value():
            b.b.name = 4 
        self.assertRaises(BadValueError, bad_value)

        b1 = B()
        try:
            b1.b.name = 3
            raise RuntimeError
        except BadValueError:
            pass
        b1.b.name = u"test"

    def testSchemaProperty2(self):
        class DocOne(Document):
            name = StringProperty()

        class DocTwo(Document):
            name = StringProperty()
            one = SchemaProperty(DocOne())

        class DocThree(Document):
            name = StringProperty()
            two = SchemaProperty(DocTwo())

        one = DocOne(name='one')
        two = DocTwo(name='two', one=one)
        three = DocThree(name='three', two=two)
        self.assert_(three.two.one.name == 'one')

    def testSchemaPropertyDefault(self):
        class DocOne(DocumentSchema):
            name = StringProperty()
            
        class DocTwo(Document):
            one = SchemaProperty(DocOne, default=DocOne(name='12345'))
        
        two = DocTwo()
        self.assert_(two.one.name == '12345')
        
    def testSchemaPropertyDefault2(self):
        class DocOne(DocumentSchema):
            name = StringProperty()
            field2 = StringProperty(default='54321')
                    
        default_one = DocOne()
        default_one.name ='12345'
        
        class DocTwo(Document):
            one = SchemaProperty(DocOne, default=default_one)
        
        two = DocTwo()
        self.assert_(two.one.name == '12345')
        self.assert_(two.one.field2 == '54321')
    
    def testSchemaPropertyDefault3(self):
        class DocOne(Document):
            name = StringProperty()
            
        class DocTwo(Document):
            one = SchemaProperty(DocOne, default=DocOne(name='12345'))

        two = DocTwo()
        self.assert_(two.one.name == '12345')
    
    def testSchemaPropertyDefault4(self):
        class DocOne(Document):
            name = StringProperty()
            field2 = StringProperty(default='54321')
        
        default_one = DocOne()
        default_one.name ='12345'
        
        class DocTwo(Document):
            one = SchemaProperty(DocOne, default=default_one)
        
        two = DocTwo()
        self.assert_(two.one.name == '12345')
        self.assert_(two.one.field2 == '54321')
        
    def testSchemaWithPythonTypes(self):
        class A(Document):
            c = unicode()
            i = int(4)
        a = A()
        self.assert_(a._doc == {'c': u'', 'doc_type': 'A', 'i': 4})
        def bad_value():
            a.i = "essai"

        self.assertRaises(BadValueError, bad_value)
        
    def testValueNone(self):
        class A(Document):
            s = StringProperty()
        a = A()
        a.s = None
        self.assert_(a._doc['s'] is None)
        A._db = self.db
        a.save()
        b = A.get(a._id)
        self.assert_(b.s is None)
        self.assert_(b._doc['s'] is None)

    def testSchemaBuild(self):
        schema = DocumentSchema(i = IntegerProperty())
        C = DocumentSchema.build(**schema._dynamic_properties)
        self.assert_('i' in C._properties)
        self.assert_(isinstance(C.i, IntegerProperty))

        c = C()
        self.assert_(c._doc_type == 'AnonymousSchema')
        self.assert_(c._doc == {'doc_type': 'AnonymousSchema', 'i':
            None})


        schema2 = DocumentSchema(i = IntegerProperty(default=-1))
        C3 = DocumentSchema.build(**schema2._dynamic_properties)
        c3 = C3()

        self.assert_(c3._doc == {'doc_type': 'AnonymousSchema', 'i':
            -1})
        self.assert_(c3.i == -1)

        def bad_value():
            c3.i = "test"

        self.assertRaises(BadValueError, bad_value)
        self.assert_(c3.i == -1)

    def testSchemaPropertyValidation2(self):
        class Foo( Document ):
            bar = SchemaProperty(DocumentSchema(foo=IntegerProperty()))

        doc = Foo()
        def bad_value():
            doc.bar.foo = "bla"
        self.assertRaises(BadValueError, bad_value)
    
   
    def testDynamicSchemaProperty(self):
        from datetime import datetime
        class A(DocumentSchema):
            s = StringProperty()
            
        a = A(s="foo")

        class B(Document):
            s1 = StringProperty()
            s2 = StringProperty()
            sm = SchemaProperty(a)
        
        b = B()
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': u'foo'}})

        b.created = datetime(2009, 2, 6, 18, 58, 20, 905556)
        self.assert_(b._doc == {'created': '2009-02-06T18:58:20Z',
            'doc_type': 'B',
            's1': None,
            's2': None,
            'sm': {'doc_type': 'A', 's': u'foo'}})

        self.assert_(isinstance(b.created, datetime) == True)

        a.created = datetime(2009, 2, 6, 20, 58, 20, 905556)
        self.assert_(a._doc ==  {'created': '2009-02-06T20:58:20Z',
            'doc_type': 'A', 's': u'foo'})

        self.assert_(b._doc == {'created': '2009-02-06T18:58:20Z',
            'doc_type': 'B',
            's1': None,
            's2': None,
            'sm': {'created': '2009-02-06T20:58:20Z', 'doc_type': 'A',
            's': u'foo'}})


        b2 = B()
        b.s1 = "t1"

        self.assert_(b2.sm._doc == b.sm._doc)
        self.assert_(b.s1 != b2.s1)

        b2.sm.s3 = "t2"
        self.assert_(b2.sm.s3 == b.sm.s3)
        self.assert_(b.s1 != b2.s1)

        b.sm.s3 = "t3"
        self.assert_(b2.sm.s3 == "t3")

    def testStaticSchemaProperty(self):
        from datetime import datetime
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            s1 = StringProperty()
            s2 = StringProperty()
            sm = SchemaProperty(A)
       
        b = B()
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': None}})

        b.sm.s = "t1"
        self.assert_(b._doc == {'doc_type': 'B', 's1': None, 's2': None,
            'sm': {'doc_type': 'A', 's': u't1'}})

        b2 = B()
        self.assert_(b2._doc == {'doc_type': 'B', 's1': None, 's2':
            None, 'sm': {'doc_type': 'A', 's': None}})

        b2.sm.s = "t2"
        self.assert_(b2._doc == {'doc_type': 'B', 's1': None, 's2':
            None, 'sm': {'doc_type': 'A', 's': u't2'}})

        self.assert_(b2.sm.s != b.sm.s)
        
    def testSchemaListProperty(self):
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)
            
        b = B()
        self.assert_(b.slm == [])
        
        a = A()
        a.s = "test"
        b.slm.append(a)
        self.assert_(b._doc == {'doc_type': 'B', 'slm': [{'doc_type': 'A', 's': u'test'}]})
        a1 = A()
        a1.s = "test2"
        b.slm.append(a1)
        self.assert_(b._doc == {'doc_type': 'B', 'slm': [{'doc_type': 'A', 's': u'test'}, {'doc_type': 'A', 's': u'test2'}]})
        
        B.set_db(self.db) 
        b.save()
        b1 = B.get(b._id)
        self.assert_(len(b1.slm) == 2)
        self.assert_(b1.slm[0].s == "test")


    def testSchemaListPropertySlice(self):
        """SchemaListProperty slice methods
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        a3 = A()
        a3.s = 'test3'
        b.slm[0:1] = [a1, a2]
        self.assertEqual(len(b.slm), 2)
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })
        b.slm.append(a3)
        c = b.slm[1:3]
        self.assertEqual(len(c), 2)
        self.assertEqual([c[0].s, c[1].s], [a2.s, a3.s])
        del b.slm[1:3]
        self.assertEqual(len(b.slm), 1)
        self.assertEqual(b.slm[0].s, a1.s)
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)}]
        })


    def testSchemaListPropertyContains(self):
        """SchemaListProperty contains method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a1]
        self.assertTrue(a1 in b.slm)
        self.assertFalse(a2 in b.slm)


    def testSchemaListPropertyCount(self):
        """SchemaListProperty count method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a1, a2, a1]
        self.assertEqual(b.slm.count(a1), 2)


    def testSchemaListPropertyExtend(self):
        """SchemaListProperty extend method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm.extend([a1, a2])
        self.assertEqual(len(b.slm), 2)
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })


    def testSchemaListPropertyIndex(self):
        """SchemaListProperty index method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        a3 = A()
        a3.s = 'test3'
        b.slm = [a1, a2, a1, a2, a1]
        self.assertEqual(b.slm.index(a1), 0)
        self.assertEqual(b.slm.index(a2, 2), 3)
        self.assertEqual(b.slm.index(a1, 1, 3), 2)
        self.assertEqual(b.slm.index(a1, 1, -2), 2)
        with self.assertRaises(ValueError) as cm:
            b.slm.index(a3)
        self.assertEqual(str(cm.exception), 'list.index(x): x not in list')


    def testSchemaListPropertyInsert(self):
        """SchemaListProperty insert method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        a3 = A()
        a3.s = 'test3'
        b.slm = [a1, a3]
        b.slm.insert(1, a2)
        self.assertEqual(len(b.slm), 3)
        self.assertEqual(
            [b.slm[0].s, b.slm[1].s, b.slm[2].s], [a1.s, a2.s, a3.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)},
                    {'doc_type': 'A', 's': unicode(a3.s)}]
        })


    def testSchemaListPropertyPop(self):
        """SchemaListProperty pop method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        a3 = A()
        a3.s = 'test3'
        b.slm = [a1, a2, a3]
        v = b.slm.pop()
        self.assertEqual(v.s, a3.s)
        self.assertEqual(len(b.slm), 2)
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })
        v = b.slm.pop(0)
        self.assertEqual(v.s, a1.s)
        self.assertEqual(len(b.slm), 1)
        self.assertEqual(b.slm[0].s, a2.s)
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a2.s)}]
        })


    def testSchemaListPropertyRemove(self):
        """SchemaListProperty remove method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a1, a2]
        b.slm.remove(a1)
        self.assertEqual(len(b.slm), 1)
        self.assertEqual(b.slm[0].s, a2.s)
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a2.s)}]
        })
        with self.assertRaises(ValueError) as cm:
            b.slm.remove(a1)
        self.assertEqual(str(cm.exception), 'list.remove(x): x not in list')


    def testSchemaListPropertyReverse(self):
        """SchemaListProperty reverse method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a1, a2]
        b.slm.reverse()
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a2.s, a1.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a2.s)},
                    {'doc_type': 'A', 's': unicode(a1.s)}]
        })


    def testSchemaListPropertySort(self):
        """SchemaListProperty sort method
        """
        class A(DocumentSchema):
            s = StringProperty()
            
        class B(Document):
            slm = SchemaListProperty(A)

        b = B()
        a1 = A()
        a1.s = 'test1'
        a2 = A()
        a2.s = 'test2'
        b.slm = [a2, a1]
        b.slm.sort(key=lambda item: item['s'])
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })
        b.slm.sort(key=lambda item: item['s'], reverse=True)
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a2.s, a1.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a2.s)},
                    {'doc_type': 'A', 's': unicode(a1.s)}]
        })
        b.slm.sort(cmp=lambda x, y: cmp(x['s'].lower(), y['s'].lower()))
        self.assertEqual([b.slm[0].s, b.slm[1].s], [a1.s, a2.s])
        self.assertEqual(b._doc, {
            'doc_type': 'B',
            'slm': [{'doc_type': 'A', 's': unicode(a1.s)},
                    {'doc_type': 'A', 's': unicode(a2.s)}]
        })


    def testSchemaDictProperty(self):
        class A(DocumentSchema):
            i = IntegerProperty()

        class B(Document):
            d = SchemaDictProperty(A)

        a1 = A()
        a1.i = 123
        self.assert_(a1._doc == {'i': 123, 'doc_type': 'A'})

        a2 = A()
        a2.i = 42
        self.assert_(a2._doc == {'i': 42, 'doc_type': 'A'})

        b = B()
        b.d['v1'] = a1
        b.d[23]   = a2
        self.assert_(b._doc == {'doc_type': 'B', 'd': {"v1": {'i': 123, 'doc_type': 'A'}, '23': {'i': 42, 'doc_type': 'A'}}})

        b.set_db(self.db)
        b.save()

        b1 = B.get(b._id)
        self.assert_(len(b1.d) == 2)
        self.assert_(b1.d['v1'].i == 123)
        self.assert_(b1.d[23].i == 42)


    def testListProperty(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(datetime)
        A.set_db(self.db) 
            
        # we can save an empty list
        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'l': []})
        a.save()
        self.assert_(a['_id'])
        self.assert_(a['l']==[])
        
        a = A()
        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.l.append(d)
        self.assert_(len(a.l) == 1)
        self.assert_(a.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z']})
        a.l.append({ 's': "test"})
        self.assert_(a.l == [datetime(2009, 4, 13, 22, 56, 10), {'s': 'test'}])
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z', {'s': 'test'}]}
        )
        
        a.save()
        
        b = A.get(a._id)
        self.assert_(len(b.l) == 2)
        self.assert_(b.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(b._doc['l'] == ['2009-04-13T22:56:10Z', {'s': 'test'}])
        
        
        a = A(l=["a", "b", "c"])
        a.save()
        b = self.db.get(a._id, wrapper=A.wrap)
        self.assert_(a.l == ["a", "b", "c"])
        b.l = []
        self.assert_(b.l == [])
        self.assert_(b.to_json()['l'] == [])
        
        
    def testListPropertyNotEmpty(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(datetime, required=True)

        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'l': []})
        self.assertRaises(BadValueError, a.save)
        try:
            a.validate()
        except BadValueError, e:
            pass
        self.assert_(str(e) == 'Property l is required.')
        
        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.l.append(d)
        self.assert_(len(a.l) == 1)
        self.assert_(a.l[0] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'l': ['2009-04-13T22:56:10Z']})
        a.validate()
        
        class A2(Document):
            l = ListProperty()
            
        a2 = A2()            
        self.assertTrue(a2.validate(required=False))
        self.assertTrue(a2.validate())


    def testListPropertyWithType(self):
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)
        a = A()    
        a.l.append("test")
        self.assertRaises(BadValueError, a.validate)
        
        class B(Document):
            ls = StringListProperty()
        b = B()
        b.ls.append(u"test")
        self.assertTrue(b.validate())
        b.ls.append(datetime.utcnow())
        self.assertRaises(BadValueError, b.validate)
        
        b1  = B()
        b1.ls = [u'hello', u'123']
        self.assert_(b1.ls == [u'hello', u'123'])
        self.assert_(b1._doc['ls'] == [u'hello', u'123'])

        self.assert_(b1.ls.index(u'hello') == 0)
        b1.ls.remove(u'hello')
        self.assert_(u'hello' not in b1.ls)


    def testListPropertyExtend(self):
        """list extend method for property w/o type
        """
        class A(Document):
            l = ListProperty()

        a = A()
        a.l.extend([42, 24])
        self.assert_(a.l == [42, 24])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [42, 24]})


    def testListPropertyExtendWithType(self):
        """list extend method for property w/ type
        """
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)

        a = A()
        d1 = datetime(2011, 3, 11, 21, 31, 1)
        d2 = datetime(2011, 11, 3, 13, 12, 2)
        a.l.extend([d1, d2])
        self.assert_(a.l == [d1, d2])
        self.assert_(a._doc == {
            'doc_type': 'A',
            'l': ['2011-03-11T21:31:01Z', '2011-11-03T13:12:02Z']
        })


    def testListPropertyInsert(self):
        """list insert method for property w/o type
        """
        class A(Document):
            l = ListProperty()

        a = A()
        a.l = [42, 24]
        a.l.insert(1, 4224)
        self.assertEqual(a.l, [42, 4224, 24])
        self.assertEqual(a._doc, {'doc_type': 'A', 'l': [42, 4224, 24]})


    def testListPropertyInsertWithType(self):
        """list insert method for property w/ type
        """
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)

        a = A()
        d1 = datetime(2011, 3, 11, 21, 31, 1)
        d2 = datetime(2011, 11, 3, 13, 12, 2)
        d3 = datetime(2010, 1, 12, 3, 2, 3)
        a.l = [d1, d3]
        a.l.insert(1, d2)
        self.assertEqual(a.l, [d1, d2, d3])
        self.assertEqual(a._doc, {
            'doc_type': 'A',
            'l': ['2011-03-11T21:31:01Z',
                  '2011-11-03T13:12:02Z',
                  '2010-01-12T03:02:03Z']
        })


    def testListPropertyPop(self):
        """list pop method for property w/o type
        """
        class A(Document):
            l = ListProperty()

        a = A()
        a.l = [42, 24, 4224]
        v = a.l.pop()
        self.assert_(v == 4224)
        self.assert_(a.l == [42, 24])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [42, 24]})
        v = a.l.pop(0)
        self.assert_(v == 42)
        self.assert_(a.l == [24])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [24]})


    def testListPropertyPopWithType(self):
        """list pop method for property w/ type
        """
        from datetime import datetime
        class A(Document):
            l = ListProperty(item_type=datetime)

        a = A()
        d1 = datetime(2011, 3, 11, 21, 31, 1)
        d2 = datetime(2011, 11, 3, 13, 12, 2)
        d3 = datetime(2010, 1, 12, 3, 2, 3)
        a.l = [d1, d2, d3]
        v = a.l.pop()
        self.assertEqual(v, d3)
        self.assertEqual(a.l, [d1, d2])

         
    def testDictProperty(self):
        from datetime import datetime
        class A(Document):
            d = DictProperty()
        A.set_db(self.db)
            
        a = A()
        self.assert_(a._doc == {'d': {}, 'doc_type': 'A'})
        a.d['s'] = 'test'
        self.assert_(a._doc == {'d': {'s': 'test'}, 'doc_type': 'A'})
        a.d['created'] = datetime(2009, 4, 16, 16, 5, 41)
        self.assert_(a._doc == {'d': {'created': '2009-04-16T16:05:41Z', 's': 'test'}, 'doc_type': 'A'})
        self.assert_(isinstance(a.d['created'], datetime) == True)
        a.d.update({'s2': 'test'})
        self.assert_(a.d['s2'] == 'test')
        a.d.update({'d2': datetime(2009, 4, 16, 16, 5, 41)})
        self.assert_(a._doc['d']['d2'] == '2009-04-16T16:05:41Z')
        self.assert_(a.d['d2'] == datetime(2009, 4, 16, 16, 5, 41))
        self.assert_(a.d == {'s2': 'test', 's': 'test', 'd2': datetime(2009, 4, 16, 16, 5, 41), 'created': datetime(2009, 4, 16, 16, 5, 41)})
        
        a = A()
        a.d['test'] = { 'a': datetime(2009, 5, 10, 21, 19, 21, 127380) }
        self.assert_(a.d == { 'test': {'a': datetime(2009, 5, 10, 21, 19, 21)}})
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z'}}, 'doc_type': 'A'} )
        
        a.d['test']['b'] = "essai"
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}}, 'doc_type': 'A'})
        
        a.d['essai'] = "test"
        self.assert_(a.d == {'essai': 'test',
         'test': {'a': datetime(2009, 5, 10, 21, 19, 21),
                  'b': 'essai'}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}},
         'doc_type': 'A'})
         
        del a.d['test']['a']
        self.assert_(a.d == {'essai': 'test', 'test': {'b': 'essai'}})
        self.assert_(a._doc ==  {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})
        
        a.d['test']['essai'] = { "a": datetime(2009, 5, 10, 21, 21, 11) }
        self.assert_(a.d == {'essai': 'test',
         'test': {'b': 'essai',
                  'essai': {'a': datetime(2009, 5, 10, 21, 21, 11)}}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test',
               'test': {'b': 'essai', 'essai': {'a': '2009-05-10T21:21:11Z'}}},
         'doc_type': 'A'}
        )
        
        del a.d['test']['essai']
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})
        
        a = A()
        a.d['s'] = "level1"
        a.d['d'] = {}
        a.d['d']['s'] = "level2"
        self.assert_(a._doc == {'d': {'d': {'s': 'level2'}, 's': 'level1'}, 'doc_type': 'A'})
        a.save()
        a1 = A.get(a._id)
        a1.d['d']['s'] = "level2 edited"
        self.assert_(a1.d['d']['s'] == "level2 edited")
        self.assert_(a1._doc['d']['d']['s'] == "level2 edited")
        
    def testDictPropertyNotEmpty(self):
        from datetime import datetime
        class A(Document):
            d = DictProperty(required=True)
        A.set_db(self.db) 

        a = A()
        self.assert_(a._doc == {'doc_type': 'A', 'd': {}})
        self.assertRaises(BadValueError, a.save)
        try:
            a.save()
        except BadValueError, e:
            pass
        self.assert_(str(e) == 'Property d is required.')
        
        d = datetime(2009, 4, 13, 22, 56, 10, 967388)
        a.d['date'] = d
        self.assert_(a.d['date'] == datetime(2009, 4, 13, 22, 56, 10))
        self.assert_(a._doc == {'doc_type': 'A', 'd': { 'date': '2009-04-13T22:56:10Z' }})
        a.save()
        
        class A2(Document):
            d = DictProperty()
        a2 = A2()            
        self.assertTrue(a2.validate(required=False))
        self.assertTrue(a2.validate())
        
    def testDynamicDictProperty(self):
        from datetime import datetime
        class A(Document):
            pass
            
        a = A()
        a.d = {}
        
        a.d['test'] = { 'a': datetime(2009, 5, 10, 21, 19, 21, 127380) }
        self.assert_(a.d == {'test': {'a': datetime(2009, 5, 10, 21, 19, 21, 127380)}})
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z'}}, 'doc_type': 'A'} )
        
        a.d['test']['b'] = "essai"
        self.assert_(a._doc == {'d': {'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}}, 'doc_type': 'A'})
        
        a.d['essai'] = "test"
        self.assert_(a.d == {'essai': 'test',
         'test': {'a': datetime(2009, 5, 10, 21, 19, 21, 127380),
                  'b': 'essai'}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'a': '2009-05-10T21:19:21Z', 'b': 'essai'}},
         'doc_type': 'A'})
         
        del a.d['test']['a']
        self.assert_(a.d == {'essai': 'test', 'test': {'b': 'essai'}})
        self.assert_(a._doc ==  {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})
        
        a.d['test']['essai'] = { "a": datetime(2009, 5, 10, 21, 21, 11, 425782) }
        self.assert_(a.d == {'essai': 'test',
         'test': {'b': 'essai',
                  'essai': {'a': datetime(2009, 5, 10, 21, 21, 11, 425782)}}}
        )
        self.assert_(a._doc == {'d': {'essai': 'test',
               'test': {'b': 'essai', 'essai': {'a': '2009-05-10T21:21:11Z'}}},
         'doc_type': 'A'}
        )
        
        del a.d['test']['essai']
        self.assert_(a._doc == {'d': {'essai': 'test', 'test': {'b': 'essai'}}, 'doc_type': 'A'})
        
    def testDynamicDictProperty2(self):
        from datetime import datetime
        class A(Document):
            pass
        
        A.set_db(self.db)
        
        a = A()
        a.s = "test"
        a.d = {}
        a.d['s'] = "level1"
        a.d['d'] = {}
        a.d['d']['s'] = "level2"
        self.assert_(a._doc == {'d': {'d': {'s': 'level2'}, 's': 'level1'}, 'doc_type': 'A', 's': u'test'})
        a.save()
        
        a1 = A.get(a._id)
        a1.d['d']['s'] = "level2 edited"
        self.assert_(a1.d['d']['s'] == "level2 edited")

        self.assert_(a1._doc['d']['d']['s'] == "level2 edited")
        
        class A2(Document):
            pass
        A2.set_db(self.db) 
        a = A2(l=["a", "b", "c"])
        a.save()
        b = self.db.get(a._id, wrapper=A2.wrap)
        self.assert_(b.l == ["a", "b", "c"])
        b.l = []
        self.assert_(b.l == [])
        self.assert_(b.to_json()['l'] == [])
    
    def testDictPropertyPop(self):
        class A(Document):
            x = DictProperty()
            
        a = A()
        self.assert_(a.x.pop('nothing', None) == None)
        
    def testDictPropertyPop2(self):
        class A(Document):
            x = DictProperty()
            
        a = A()
        a.x['nothing'] = 'nothing'
        self.assert_(a.x.pop('nothing') == 'nothing')
        self.assertRaises(KeyError, a.x.pop, 'nothing')
        
    def testDynamicListProperty(self):
        from datetime import datetime
        class A(Document):
            pass
        
        A.set_db(self.db)
        
        a = A()
        a.l = []
        a.l.append(1)
        a.l.append(datetime(2009, 5, 12, 13, 35, 9, 425701))
        a.l.append({ 's': "test"})
        self.assert_(a.l == [1, datetime(2009, 5, 12, 13, 35, 9, 425701), {'s': 'test'}])
        self.assert_(a._doc == {'doc_type': 'A', 'l': [1, '2009-05-12T13:35:09Z', {'s': 'test'}]}
        )
        a.l[2]['date'] = datetime(2009, 5, 12, 13, 35, 9, 425701)
        self.assert_(a._doc == {'doc_type': 'A',
         'l': [1,
               '2009-05-12T13:35:09Z',
               {'date': '2009-05-12T13:35:09Z', 's': 'test'}]}
        )
        a.save()
        
        a1 = A.get(a._id)
        self.assert_(a1.l == [1,
         datetime(2009, 5, 12, 13, 35, 9),
         {u'date': datetime(2009, 5, 12, 13, 35, 9), u's': u'test'}]
        )
        
        a.l[2]['s'] = 'test edited'
        self.assert_(a.l == [1,
         datetime(2009, 5, 12, 13, 35, 9, 425701),
         {'date': datetime(2009, 5, 12, 13, 35, 9, 425701),
          's': 'test edited'}]
        )
        self.assert_(a._doc['l'] == [1,
         '2009-05-12T13:35:09Z',
         {'date': '2009-05-12T13:35:09Z', 's': 'test edited'}]
        )
        
        
        design_doc = {
            '_id': '_design/test',
            'language': 'javascript',
            'views': {
                'all': {
                    "map": """function(doc) { if (doc.doc_type == "A") { emit(doc._id, doc);
}}"""
                }
            }
        }
        self.db.save_doc(design_doc)
        
        a2 = A()
        a2.l = []
        a2.l.append(7)
        a2.save()
        docs = A.view('test/all')
        self.assert_(len(docs) == 2)
        
        a3 = A()
        a3.l = []
        a3.save()
        docs = A.view('test/all')
        self.assert_(len(docs) == 3)
        
        a = A(l = [1, 2])
        self.assert_(a.l == [1,2])
        self.assert_(a._doc['l'] == [1,2])
        
        a = A()
        a.l = [1, 2]
        self.assert_(a.l == [1,2])
        self.assert_(a._doc['l'] == [1,2])
        

        class A2(Document):
            pass
        A2.set_db(self.db) 
        a = A2(d={"a": 1, "b": 2, "c": 3})
        a.save()
        b = self.db.get(a._id, wrapper=A2.wrap)
        self.assert_(b.d == {"a": 1, "b": 2, "c": 3})
        b.d = {}
        self.assert_(b.d == {})
        self.assert_(b.to_json()['d'] == {})




class SetPropertyTestCase(unittest.TestCase):
    def testSetPropertyConstructor(self):
        """SetProperty constructor including default & item_type args
        """
        class A(Document):
            s = SetProperty()
        class B(Document):
            s = SetProperty(default=set((42, 24)))

        a = A()
        self.assertEqual(a._doc, {'doc_type': 'A', 's': []})
        b = B()
        self.assertEqual(b._doc['doc_type'], 'B')
        self.assertItemsEqual(b._doc['s'], [42, 24])
        with self.assertRaises(ValueError) as cm:
            class C(Document):
                s = SetProperty(item_type=tuple)
        self.assertIn(
            "item_type <type 'tuple'> not in set([", str(cm.exception))


    def testSetPropertyAssignment(self):
        """SetProperty value assignment, len, in & not in
        """
        class A(Document):
            s = SetProperty()

        a = A()
        a.s = set(('foo', 'bar'))
        self.assertEqual(a.s, set(('foo', 'bar')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar'])
        self.assertEqual(len(a.s), 2)
        self.assertEqual(len(a._doc['s']), 2)
        self.assertIn('foo', a.s)
        self.assertIn('foo', a._doc['s'])
        self.assertNotIn('baz', a.s)
        self.assertNotIn('baz', a._doc['s'])


    def testSetPropertyAssignmentWithType(self):
        """SetProperty value assignment, len, in & not in w/ type
        """
        from datetime import datetime
        class A(Document):
            s = SetProperty(item_type=datetime)

        d1 = datetime(2011, 3, 15, 17, 8, 1)
        a = A()
        a.s = set((d1, ))
        self.assertEqual(a.s, set((d1, )))
        self.assertItemsEqual(a._doc['s'], ['2011-03-15T17:08:01Z'])
        self.assertEqual(len(a.s), 1)
        self.assertEqual(len(a._doc['s']), 1)
        self.assertIn(d1, a.s)
        self.assertIn('2011-03-15T17:08:01Z', a._doc['s'])
        self.assertNotIn(datetime(2011, 3, 16, 10, 37, 2), a.s)
        self.assertNotIn('2011-03-16T10:37:02Z', a._doc['s'])


    def testSetPropertySubSuperDisjoint(self):
        """SetProperty Python subset, superset & disjoint operators work
        """
        class A(Document):
            s = SetProperty()

        iter1 = ('foo', 'bar')
        a = A()
        a.s = set(iter1)
        self.assertTrue(a.s.issubset(iter1))
        self.assertTrue(a.s <= set(iter1))
        iter2 = ('foo', 'bar', 'baz')
        self.assertTrue(a.s < set(iter2))
        self.assertTrue(a.s.issuperset(iter1))
        self.assertTrue(a.s >= set(iter1))
        iter2 = ('foo', )
        self.assertTrue(a.s > set(iter2))
        iter2 = ('bam', 'baz')
        self.assertTrue(a.s.isdisjoint(iter2))


    def testSetPropertyUnionIntersectionDifferences(self):
        """SetProperty Python union, intersection & differences operators work
        """
        class A(Document):
            s = SetProperty()

        iter1 = ('foo', 'bar')
        iter2 = ('bar', 'baz')
        iter3 = ('bar', 'fiz')
        a = A()
        a.s = set(iter1)
        # Union
        b = a.s.union(iter2)
        self.assertEqual(b, set(('foo', 'bar', 'baz')))
        b = a.s.union(iter2, iter3)
        self.assertEqual(b, set(('foo', 'bar', 'baz', 'fiz')))
        b = a.s | set(iter2)
        self.assertEqual(b, set(('foo', 'bar', 'baz')))
        b = a.s | set(iter2) | set(iter3)
        self.assertEqual(b, set(('foo', 'bar', 'baz', 'fiz')))
        # Intersection
        b = a.s.intersection(iter2)
        self.assertEqual(b, set(('bar', )))
        b = a.s.intersection(iter2, iter3)
        self.assertEqual(b, set(('bar', )))
        b = a.s & set(iter2)
        self.assertEqual(b, set(('bar', )))
        b = a.s & set(iter2) & set(iter3)
        self.assertEqual(b, set(('bar', )))
        # Difference
        b = a.s.difference(iter2)
        self.assertEqual(b, set(('foo', )))
        b = a.s.difference(iter2, iter3)
        self.assertEqual(b, set(('foo', )))
        b = a.s - set(iter2)
        self.assertEqual(b, set(('foo', )))
        b = a.s - set(iter2) - set(iter3)
        self.assertEqual(b, set(('foo', )))
        # Symmetric difference
        self.assertEqual(a.s.symmetric_difference(iter2), set(('foo', 'baz')))
        self.assertEqual(a.s ^ set(iter2), set(('foo', 'baz')))


    def testSetPropertyCopy(self):
        """SetProperty Python shallow copy method works
        """
        class A(Document):
            s = SetProperty()

        a = A()
        a.s = set(('foo', 'bar'))
        b = a.s.copy()
        self.assertIsNot(b, a.s)


    def testSetPropertyUpdate(self):
        """SetProperty update method keeps Python set & _doc list in sync
        """
        class A(Document):
            s = SetProperty()

        iter1 = ('foo', 'bar')
        iter2 = ('bar', 'baz')
        iter3 = ('baz', 'fiz')
        a = A()
        a.s = set(iter1)
        a.s.update(iter1)
        self.assertEqual(a.s, set(('foo', 'bar')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar'])
        a.s = set(iter1)
        a.s.update(iter2)
        self.assertEqual(a.s, set(('foo', 'bar', 'baz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz'])
        a.s = set(iter1)
        a.s.update(iter2, iter3)
        self.assertEqual(a.s, set(('foo', 'bar', 'baz', 'fiz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz', 'fiz'])
        a.s = set(iter1)
        a.s |= set(iter2)
        self.assertEqual(a.s, set(('foo', 'bar', 'baz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz'])
        a.s = set(iter1)
        a.s |= set(iter2) | set(iter3)
        self.assertEqual(a.s, set(('foo', 'bar', 'baz', 'fiz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz', 'fiz'])


    def testSetPropertyIntersectionUpdate(self):
        """SetProperty intersection_update method keeps Python & _doc in sync
        """
        class A(Document):
            s = SetProperty()

        iter1 = ('foo', 'baz')
        iter2 = ('bar', 'baz')
        iter3 = ('bar', 'fiz')
        a = A()
        a.s = set(iter1)
        a.s.intersection_update(iter1)
        self.assertEqual(a.s, set(('foo', 'baz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'baz'])
        a.s = set(iter1)
        a.s.intersection_update(iter2)
        self.assertEqual(a.s, set(('baz', )))
        self.assertItemsEqual(a._doc['s'], ['baz'])
        a.s = set(iter1)
        a.s.intersection_update(iter2, iter3)
        self.assertEqual(a.s, set())
        self.assertItemsEqual(a._doc['s'], [])
        a.s = set(iter1)
        a.s &= set(iter2)
        self.assertEqual(a.s, set(('baz', )))
        self.assertItemsEqual(a._doc['s'], ['baz'])
        a.s = set(iter1)
        a.s &= set(iter2) & set(iter3)
        self.assertEqual(a.s, set())
        self.assertItemsEqual(a._doc['s'], [])


    def testSetPropertyDifferenceUpdate(self):
        """SetProperty difference_update method keeps Python & _doc in sync
        """
        class A(Document):
            s = SetProperty()

        iter1 = ('foo', 'baz', 'fiz')
        iter2 = ('bar', 'baz')
        iter3 = ('bar', 'fiz')
        a = A()
        a.s = set(iter1)
        a.s.difference_update(iter1)
        self.assertEqual(a.s, set())
        self.assertEqual(a._doc['s'], [])
        a.s = set(iter1)
        a.s.difference_update(iter2)
        self.assertEqual(a.s, set(('foo', 'fiz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'fiz'])
        a.s = set(iter1)
        a.s.difference_update(iter2, iter3)
        self.assertEqual(a.s, set(('foo', )))
        self.assertItemsEqual(a._doc['s'], ['foo'])
        a.s = set(iter1)
        a.s -= set(iter1)
        self.assertEqual(a.s, set())
        self.assertEqual(a._doc['s'], [])
        a.s = set(iter1)
        a.s -= set(iter2)
        self.assertEqual(a.s, set(('foo', 'fiz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'fiz'])
        a.s = set(iter1)
        a.s -= set(iter2) | set(iter3)
        self.assertEqual(a.s, set(('foo', )))
        self.assertItemsEqual(a._doc['s'], ['foo'])


    def testSetPropertySymmetricDifferenceUpdate(self):
        """SetProperty difference_update method keeps Python & _doc in sync
        """
        class A(Document):
            s = SetProperty()

        iter1 = ('foo', 'baz', 'fiz')
        iter2 = ('bar', 'baz')
        a = A()
        a.s = set(iter1)
        a.s.symmetric_difference_update(iter1)
        self.assertEqual(a.s, set())
        self.assertEqual(a._doc['s'], [])
        a.s = set(iter1)
        a.s.symmetric_difference_update(iter2)
        self.assertEqual(a.s, set(('foo', 'bar', 'fiz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'fiz'])
        a.s = set(iter1)
        a.s ^= set(iter1)
        self.assertEqual(a.s, set())
        self.assertEqual(a._doc['s'], [])
        a.s = set(iter1)
        a.s ^= set(iter2)
        self.assertEqual(a.s, set(('foo', 'bar', 'fiz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'fiz'])


    def testSetPropertyAdd(self):
        """SetProperty add method works
        """
        class A(Document):
            s = SetProperty()

        a = A()
        a.s = set(('foo', 'bar'))
        a.s.add('bar')
        self.assertEqual(a.s, set(('foo', 'bar')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar'])
        a.s.add('baz')
        self.assertEqual(a.s, set(('foo', 'bar', 'baz')))
        self.assertItemsEqual(a._doc['s'], ['foo', 'bar', 'baz'])


    def testSetPropertyRemove(self):
        """SetProperty remove method works
        """
        class A(Document):
            s = SetProperty()

        a = A()
        a.s = set(('foo', 'bar'))
        a.s.remove('foo')
        self.assertEqual(a.s, set(('bar', )))
        self.assertItemsEqual(a._doc['s'], ['bar'])
        with self.assertRaises(KeyError):
            a.s.remove('foo')


    def testSetPropertyDiscard(self):
        """SetProperty discard method works
        """
        class A(Document):
            s = SetProperty()

        a = A()
        a.s = set(('foo', 'bar'))
        a.s.discard('foo')
        self.assertEqual(a.s, set(('bar', )))
        self.assertItemsEqual(a._doc['s'], ['bar'])
        a.s.discard('foo')
        self.assertEqual(a.s, set(('bar', )))
        self.assertItemsEqual(a._doc['s'], ['bar'])


    def testSetPropertyPop(self):
        """SetProperty pop method works
        """
        class A(Document):
            s = SetProperty()

        a = A()
        a.s = set(('foo', 'bar'))
        b = a.s.pop()
        self.assertNotIn(b, a.s)
        self.assertNotIn(b, a._doc['s'])
        b = a.s.pop()
        self.assertNotIn(b, a.s)
        self.assertNotIn(b, a._doc['s'])
        with self.assertRaises(KeyError):
            a.s.pop()


    def testSetPropertyClear(self):
        """SetProperty clear method works
        """
        class A(Document):
            s = SetProperty()

        a = A()
        a.s = set(('foo', 'bar'))
        a.s.clear()
        self.assertEqual(a.s, set())
        self.assertEqual(a._doc['s'], [])

        
if __name__ == '__main__':
    unittest.main()
