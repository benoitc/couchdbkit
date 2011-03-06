About
-----

`Couchdbkit`_ provides you a full featured and easy client to access and 
manage CouchDB. It allows you to manage a CouchDBserver, databases, doc 
managements and view access. All objects mostly reflect python objects for 
convenience. Server and Databases objects could be used for example as easy 
as using a dict.

Installation
------------

Couchdbkit requires Python 2.x superior to 2.5.

Install from sources::

  $ python setup.py install

Or from Pypi::

  $ easy_install -U couchdbkit
  
Getting started
---------------

This tutorial exposes key features of this library mainly through code
examples. For in-depth description of the modules, you'll want to read 
the `API`_ documentation.

Write your first CouchDB document
+++++++++++++++++++++++++++++++++

::

  from couchdbkit import Server
  # server object
  server = Server()
  
  # create database
  db = server.get_or_create_db("greeting")

  doc = {"mydoc": "test"}
  db.save_doc(doc)

::

  import datetime
  from couchdbkit import *
  
  class Greeting(Document):
      author = StringProperty()
      content = StringProperty()
      date = DateTimeProperty()


Store the submitted Greetings
+++++++++++++++++++++++++++++

Here is the code to save a greet on ``Greeting``  database. We also see how to create a database::

  from couchdbkit import Server
  
  # associate Greeting to the db
  Greeting.set_db(db)

  # create a new greet
  greet = Greeting(
      author="Benoit",
      content="Welcome to couchdbkit world",
      date=datetime.datetime.utcnow()
  )
  
  # save it 
  greet.save()

.. NOTE::

  You can just use the db object to save a Schema: ``db.save(greet)`` .


Your document ``greet`` is now in the ``greetings`` db. Each document 
is saved with a ``doc_type`` field that allow you to find easily each 
kind of document with the views. By default ``doc_type`` is the name of
the class.

Now that you saved your document, you can update it::

  greet.author = u"Benoit Chesneau"
  greet.save()

Here we updated the author name.

Dynamic properties
++++++++++++++++++

Mmm ok, but isn't CouchDB storing documents schema less? Do you want to 
add a property ? Easy::

  greet.homepage = "http://www.e-engura.org"
  greet.save()

Now you have just added an homepage property to the document.

Get all greetings
+++++++++++++++++

You first have to create a view and save it in the db. We will call it 
``greeting/all``. To do this we will use the loader system of couchdbkit 
that allows you to send views to CouchDB.

Let's create a folder that contains the design doc, and then the folder 
for the view. On unix::

  mkdir -p ~/Work/couchdbkit/example/_design/greeting/views/all

In this folder we edit a file `map.js`::

  function(doc) { 
    if (doc.doc_type == "Greeting") 
      emit(doc._id, doc); 
      }
  }

Here is a folder structure::

  /Work/couchdbkit/example/:

  --_design/
  ---- greetings
  ------ view

Here is a  screenshot:
  
.. image:: http://couchdbkit.org/images/gettingstarted.png


A system will be provided to manage view creation and other things. As
some  noticed, this system works like `couchapp`_ and is fully
compatible.

Then we use push function to send the design document to CouchDB::

  from couchdbkit.designer import push
  push('/path/to/example/_design/greetings', db)

The design doc is now in the ``greetings`` database and you can get all 
greets::

  greets = Greeting.view('greeting/all')

.. _Couchdbkit: http://couchdbkit.org
.. _API: http://couchdbkit.org/doc/api/
.. _couchapp:  http://github.com/couchapp/couchapp/tree/
