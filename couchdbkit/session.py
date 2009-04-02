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

import threading

from couchdbkit.client import Database

def create_session(server, db_name, scoped_func=None):
    return Session(server, db_name, scoped_func)

class Session(object):

    def __init__(self, server, dbname, scoped_func=None):
        self.server = server
        self.dbname = dbname
        self.registry = ScopedRegistry(self.session_factory,
                scoped_func)
    
    def __call__(self, document):
        if not hasattr(document, '_db'):
            raise TypeError('%s is not a Document object' % document)

        db = self.registry()
        document._db = db
        return document

    def save(self, document):
        """ save document in database.

        : paramms document: `schema.Document` instance
        """
        if isinstance(document, type):
            raise TypeError('only document instance could be saved')

        db = self.registry()
        document._db = db
        document.save()
        
    def get(self, document, docid):
        """ get document with docid"""
        if not isinstance(document, type):
            raise TypeError('only document class could be used')

        db = self.registry()
        document._db = db
        return document.get(docid)

    def get_or_create(self, document, docid=None):
        """ get or create a new document with docid """
        
        if not isinstance(document, type):
            raise TypeError('only document class could be used')

        db = self.registry()
        document._db = db
        return document.get_or_create(docid=docid)
        
    def view(self, document, view_name, wrapper=None, **params):
        """ query db and try to wrap results to this document object"""
        if not isinstance(document, type):
            raise TypeError('only document class could be used')

        db = self.registry()
        document._db = db
        return document.view(view_name, wrapper=wrapper, **params)

    def temp_view(self, document, design, wrapper=None, **params):
        """ temeporary query on db and try to wrap results to this document object"""
        if not isinstance(document, type):
            raise TypeError('only document class could be used')

        db = self.registry()
        document._db = db
        return document.temp_view(design, wrapper=wrapper, **params)
    
    def session_factory(self):
        return Database(self.server, self.dbname)

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
