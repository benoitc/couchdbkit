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

"""
When you need threadsafe connection to your databases, use the session
object. The session act like with database object, but all connections 
are placed in the local thread. So no more collision, lost or anything 
else, which could happend often on BSD system.
"""


import threading

from couchdbkit.client import Server, Database

def create_session(server, db_name, scoped_func=None, database_class=None):
    """
    create a threadsafe db sesson.
    
    @param server: `couchdbkit.Server` instance
    @param db_name: str, name of db
    @param scopped_function: function to get thread local ident. 
    @param database_class: custom class inheriting from `couchdbkit.Database`.
    """
    if isinstance(server, basestring):
        server = Server(server)
    
    session = Session(server, db_name, scoped_func)
    if database_class and database_class is not None:
        session._DATABASE_CLASS = database_class
    return session

class Session(object):
    """ Provide a thread local management of db.
    
    Usage:
    
        Create a session with `create_session`
        
            session = create_session(server, dbname)
            
        Then use it like db object. You can also use Session
        with `Document`objects :
            
            MyDocument = session(MyDocument)
            MyDocument.save()
            
            or :
            
            session(Mydocument).save()
            
        instead of doing :
        
            MyDocument.set_db(session) 
            MyDocument.save()


    In case you want to use your own database object,
    you could pass it to Session object by settings
    _DATABASE_CLASS property.
        
    """
    
    _DATABASE_CLASS = Database

    def __init__(self, server, dbname, scoped_func=None):
        self.server = server
        self.dbname = dbname
        self.registry = ScopedRegistry(self.session_factory,
                scoped_func)
                         
    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.dbname)
    
    def __call__(self, document):
        """ pass to session object an object with `_db` property
        it will set it with a session object you could use later
        """
        if not hasattr(document, '_db'):
            raise TypeError('%s is not a Document object' % document)

        db = self.registry()
        document._db = db
        return document
        
    def contain(self, *docs):
        """ add db session to all DocumentBase instance """
        for doc in docs:
            if hasattr(doc, '_db'):
                doc._db = self
        
    def __getattr__(self, key):
        db = self.registry()
        if not key.startswith('_') and key not in dir(self) \
                and hasattr(db, key):
            return getattr(db, key)
        return getattr(super(Session, self), key)
        
    def __len__(self):
        db = self.registry()
        return db.__len__()
        
    def __contains__(self, docid):
        db = self.registry()
        return db.__contains__(docid)
        
    def __getitem__(self, docid):
        db = self.registry()
        return db.__getitem__(docid)
        
    def __setitem__(self, docid, doc):
        db = self.registry()
        return db.__setitem__(docid, doc)
        
    def __delitem__(self, docid):
        db = self.registry()
        return db.__delitem__(docid)

    def __iter__(self):
        db = self.registry()
        return db.iterdocuments()
        
    def __nonzero__(self):
        db = self.registry()
        return (len(db) > 0)

    def session_factory(self):
        return self._DATABASE_CLASS(self.server, self.dbname)

class ScopedRegistry(object):
    """A Registry that can store one or multiple instances of a single
    class on a per-thread scoped basis, or on a customized scope.

    createfunc
      a callable that returns a new object to be placed in the registry

    scopefunc
      a callable that will return a key to store/retrieve an object.
      If None, ScopedRegistry uses a threading.local object instead.

    """
    def __new__(cls, createfunc, scopefunc=None):
        if not scopefunc:
            return object.__new__(_TLocalRegistry)
        else:
            return object.__new__(cls)

    def __init__(self, createfunc, scopefunc):
        self.createfunc = createfunc
        self.scopefunc = scopefunc
        self.registry = {}

    def __call__(self):
        key = self.scopefunc()
        try:
            return self.registry[key]
        except KeyError:
            return self.registry.setdefault(key, self.createfunc())

    def has(self):
        return self.scopefunc() in self.registry

    def set(self, obj):
        self.registry[self.scopefunc()] = obj

    def clear(self):
        try:
            del self.registry[self.scopefunc()]
        except KeyError:
            pass

class _TLocalRegistry(ScopedRegistry):
    def __init__(self, createfunc, scopefunc=None):
        self.createfunc = createfunc
        self.registry = threading.local()

    def __call__(self):
        try:
            return self.registry.value
        except AttributeError:
            val = self.registry.value = self.createfunc()
            return val

    def has(self):
        return hasattr(self.registry, "value")

    def set(self, obj):
        self.registry.value = obj

    def clear(self):
        try:
            del self.registry.value
        except AttributeError:
            pass
