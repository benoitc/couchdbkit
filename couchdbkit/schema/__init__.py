# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

""" Schema is an easy way to map couchdb object in pythoin object. It's
similar to ORMs but with all couchdb glory.

An application describes the kinds of data it uses with a Document object. A
document is a Python class that inherits from the `couchdbkit.schema.Document`
class. The document class defines a new kind of CouchDB document and the
properties the kind is expected to take.

Document properties are defined using class attributes on the document class.
Each class attribute is an instance of a subclass of the Property class,
usually one of the provided property classes. A property instance holds
configuration for the property, such as whether or not the property is required
for the instance to be valid, or a default value to use for the instance if
none is provided.


    from couchdbkit import Document

    class Pet(Document):
        name = schema.StringProperty(required=True)
        type = schema.StringProperty(required=True)
        birthdate = schema.DateProperty()
        weight_in_pounds = schema.IntegerProperty()
        spayed_or_neutered = schema.BooleanProperty()
        owner = schema.StringProperty()

An CouchDB document is represented in the API by an instance of the
corresponding document class. The application can create a new document by
calling the constructor of the class. The application accesses and manipulates
properties of the entity using attributes of the instance. The document
instance constructor accepts initial values for properties as keyword
arguments.


    pet = Pet(name="Fluffy",
          type="cat",
          owner="Jean")
    pet.weight_in_pounds = 24


  Document is dynamic
--------------------

Sometimes it is usefull to have different properties on each document. CouchDB
allows it, so why not having it in python. A document can have both dynamic and
static property. Any value assigned to an attribute of an instance of a
document becomes a property of the CouchDB document, using the name of the
attribute. These properties are known as dynamic properties. Properties defined
using Property class instances in class attributes are fixed properties.


    class Person(Document):
        first_name = schema.StringProperty()
        last_name = schema.StringProperty()
        hobbies = schema.ListProperty()

    p = Person(first_name="Albert", last_name="Johnson")
    p.hobbies = ["chess", "travel"]

    p.chess_elo_rating = 1350

    p.travel_countries_visited = ["Spain", "Italy", "USA", "Brazil"]
    p.travel_trip_count = 13

Because dynamic properties do not have document property definitions, dynamic
properties are not validated. Any dynamic property can have a value of any of
the python types, including None. 

Unlike fixed properties, dynamic properties need not exist. A dynamic property
with a value of None is different from a non-existent dynamic property.  You
can delete a dynamic property by deleting the attribute.

    del p.chess_elo_rating

A request that uses a dynamic property will only return entities whose value
for the property is of the same type as the value used in the request.
Similarly, the request will only return entities with that property set.


    p1 = Person()
    p1.favorite = 42
    db.save_doc(p1) 

    p2 = Person()
    p2.favorite = "blue"
    db.save_doc(p2)

    p3 = Person()
    db.save_doc(p3)

    people = Person.view(db, "person/favorite", startkey=0, endkey=50)
    # people has p1, but not p2 or p3

    people = Person.view(db, "person/favorite")", startkey=50)
    # people has no results


Some dynamic data in couchdb are automatically converted to their python type.
Those are datetime, datetime.date, datetime.time and Decimal types. this is
only possible if date/time fields are :rfc:`8601` strings in the couchdb
document.

Document inheritance in simplecouchdb work almost identically to the way normal
class inheritance works in Python.     

    class Animal(Document)
        name = StringProperty(required=True)
        type = StringProperty(required=True)

    class Pet(Animal):
        birthdate = DateProperty()
        weight_in_pounds = IntegerProperty()
        spayed_or_neutered = BooleanProperty()
        owner = StringProperty()

The `Pet` document will have 6 properties name, type, birthdate,
weight_in_pounds, spayed_or_neutered, owner. It can be used as a common
Document object. Pet and Animal have 2 different doc_type.

For now, there is no way in CouchDB to know that Pet inherit from Animal.
Though this feature will be implemented soon.
 

Properties and Types
--------------------

Couchdb supports all Javascript types, including Unicode strings, integers,
floating point numbers. We also added support for dates and decimal types. Each
of the CouchDB value type has a corresponding Property class provided by the
:mod:`simplecouchdb.schema` module.


Other way to save on the db.
----------------------------

If you don't want to use the db object to save doc each time and save
àla "ORM" you can fix a db to a Document class::

    class A(Dcoument):
        s = StringProperty()

    A.set_db(db)

    a = A()
    a.save()

This method isn't really threadsafe since once class will share a db
reference across threads, changing a db to a class will be applied to
all threads. It's better to use the db object methods if you want to be
threadsafe.

"""

from .properties import ALLOWED_PROPERTY_TYPES, Property, StringProperty, \
IntegerProperty, DecimalProperty, BooleanProperty, FloatProperty, \
DateTimeProperty, DateProperty, TimeProperty, DictProperty, \
ListProperty, StringListProperty, SetProperty, dict_to_json, list_to_json, \
value_to_json, MAP_TYPES_PROPERTIES, value_to_python, dict_to_python, \
list_to_python, convert_property, value_to_property, LazyDict, LazyList, \
LazySet
from .base import ReservedWordError, ALLOWED_PROPERTY_TYPES, \
DocumentSchema, SchemaProperties, DocumentBase, QueryMixin, \
AttachmentMixin, Document, StaticDocument, valid_id
from .properties_proxy import SchemaProperty, SchemaListProperty, \
SchemaDictProperty

def contain(db, *docs):
    """ associate a db to multiple `Document` class"""
    for doc in docs:
        if hasattr(doc, '_db'):
            doc._db = db
