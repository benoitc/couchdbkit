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
# Code heavyly inspired from django project under BSD license:
# Copyright (c) 2008 Django Software Foundation and individual contributors.
#

from simplecouchdb.core.design import Design
from exceptions import MultipleObjectsReturned
from simplecouchdb.resource import ResourceNotFound


__all__ = ['DesignDoc']

class DesignDoc(object):
    creation_counter = 0

    def __init__(self):
        super(DesignDoc, self).__init__()
        self._set_creation_counter()
        self._design = None
        self.document = None
        self.name = None
        self._db = None

    def __design_config__(self, document, name):
        self.document = document
        self.name = name

        #self._db = getattr(document, '_db')
        setattr(document, name, DesignDescriptor(self))
        
        if not getattr(document, '_default_design', None) or \
                self.creation_counter < document._default_design.creation_counter:
            document._default_design = self

    def _set_creation_counter(self):
        self.creation_counter = DesignDoc.creation_counter
        DesignDoc.creation_counter += 1

    def get_design(self):
        if self._db is None:
            raise TypeError("database required to fetch the view")

        if self._design is None:
            self._design = Design()
            self._design.name = "%s_%s" % (self.document.__name__, self.name)

        self._design.database = self._db
        return self._design

    def view_by(self, *args, **kwargs):
        self._parse_params(kwargs)
        if len(args) == 1 and not \
                hasattr(self.document, args[0]) \
                and not '.' in args[0]:
            kwargs['method_name'] = args[0]
            del kwargs['guards']
            return self.get_design().view_by(**kwargs)
        
        return self.get_design().view_by(*args, **kwargs)

    def all(self, **kwargs):
        self._parse_params(kwargs)
        return self.get_design().view_by('_id', **kwargs)

    def count(self, *args, **kwargs):
        return len(self.view_by(*args, **kwargs))

    def get_by(self, *args, **kwargs):
        results = self.view(*args, **kwargs)
        count = results.count()
        if count > 1:
            raise MultipleObjectsReturned,\
              "get_by() returned more than one %s (%s objects returned)" % (
                results.results_iterator().next().__class__.__name__, count)
        elif count == 1:
            return results.results()[0]
        else:
            return None
 

    #################################
    # generic all
    #################################

    def get(self, docid):
        if self._db is None:
            raise TypeError("database required to load the document")

        return self._db.get(docid, wrapper=self.document.wrap)

    def get_or_create(self, docid):
        if self._db is None:
            raise TypeError("database required to fetch the view")
        
        try:
            return self._db.get(docid, wrapper=self.document.wrap)
        except ResourceNotFound:
            obj = self.document()
            obj.id = docid
            obj.save()
            return obj

    def view(self, view_name, **params):
        """ Get documents associated to a view.
        Results of view are automatically wrapped
        to Document object.

        :params view_name: str, name of view
        :params params:  params of view

        :return: :class:`simplecouchdb.core.ViewResults` instance. All
        results are wrapped to current document instance.
        """

        def _wrapper(row):
            if not 'id' in row:
                return row
            data = row['value']
            data['_id'] = row.get('id')
            obj = self.document.wrap(data)

            return obj

        db = getattr(self.document, '_db', None)
        if not "/" in view_name:
            view_name = "%s_%s/%s" % (self.document.__name__, 
                    self.name, view_name)
        return db.view(view_name, wrapper=_wrapper, **params)

    def temp_view(self, design, **params):
        """ Slow view. Like in view method,
        results are automatically wrapped to 
        Document object.

        :params design: design object, See `simplecouchd.client.Database`
        :params params:  params of view

        :return: Like view, return a :class:`simplecouchdb.core.ViewResults` instance. All
        results are wrapped to current document instance.
        """

        def _wrapper(row):
            if not 'id' in row:
                return row
            data = row['value']
            
            data['_id'] = row.get('id')
            obj = self.document.wrap(data)
            return obj

        db = getattr(self.document, '_db', None)
        return db.temp_view(design, wrapper=_wrapper, **params)    

    #################################
    # private methods
    #################################

    def _parse_params(self, kwargs):
        def _wrapper(row):
            if not 'id' in row:
                return row
            data = row['value']
            data['_id'] = row.get('id')
            obj = self.document.wrap(data)
            return obj
        
        doctype = kwargs.pop('doctype', True)
        guards = kwargs.get('guards', [])
        if doctype:
            guards.append('doc["doc_type"] == "%s"' % self.document.__name__)
        kwargs['guards'] = guards
        kwargs['wrapper'] = _wrapper

class DesignDescriptor(object):

    def __init__(self, design_doc):
        self.design_doc = design_doc

    def __get__(self, document_instance, document_class):
        if document_instance != None:
            raise AttributeError, "Manager isn't accessible via %s instances" % type.__name__
        
        self.design_doc._db = document_class._db
        return self.design_doc 

