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

def create_session(server, db_name, scoped_func=None):
    return DBSession(server, db_name, scoped_func)
    
class DBSession(object):

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
    
    def design_doc(self, document):
        if not isinstance(document, type):
            raise AttributeError, "design_doc isn't accessible via %s instances" % type.__name__

        db = self.registry()
        document._db = db
        
        if hasattr(document, 'objects'):
            return document.objects
        
        return document.default_objects 

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