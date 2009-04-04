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


import couchdbkit
from couchdbkit.properties import Property
from couchdbkit.schema import DocumentSchema
from couchdbkit.exceptions import *


class SchemaProperty(Property):
    """ Schema property. It allow you add a DocumentSchema instance 
    a member of a Document object. It return a
    :class:`simplecouchdb.schemaDocumentSchema` object.

    Exemple :
    
        >>> from simplecouchdb.schema import *
        >>> class Blog(DocumentSchema):
        ...     title = StringProperty()
        ...     author = StringProperty(default="me")
        ... 
        >>> class Entry(Document):
        ...     title = StringProperty()
        ...     body = StringProperty()
        ...     blog = SchemaProperty(Blog())
        ... 
        >>> test = Entry()
        >>> test._doc
        {'body': None, 'doc_type': 'Entry', 'title': None, 'blog': {'doc_type': 'Blog', 'author': u'me', 'title': None}}
        >>> test.blog.title = "Mon Blog"
        >>> test._doc
        {'body': None, 'doc_type': 'Entry', 'title': None, 'blog': {'doc_type': 'Blog', 'author': u'me', 'title': u'Mon Blog'}}
        >>> test.blog.title
        u'Mon Blog'
        >>> from simplecouchdb import Server
        >>> s = Server()
        >>> db = s.create_db('simplecouchdb_test')
        >>> Entry._db = db 
        >>> test.save()
        >>> doc = Entry.objects.get(test.id)
        >>> doc.blog.title
        u'Mon Blog'
        >>> del s['simplecouchdb_test']

    """

    def __init__(self, schema, verbose_name=None, name=None, 
            required=False, validators=None, default=None):

        Property.__init__(self, verbose_name=None,
            name=None, required=False, validators=None)
       
        use_instance = True
        if type(schema) == couchdbkit.schema.SchemaProperties:
            use_instance = False    

        elif not isinstance(schema, DocumentSchema):
            raise TypeError('schema should be a DocumentSchema instance')
       
        elif schema.__class__.__name__ == 'DocumentSchema':
            use_instance = False
            properties = schema._dynamic_properties.copy()
            schema = DocumentSchema.build(**properties)
            
        self._use_instance = use_instance
        self._schema = schema
        
    def default_value(self):
        if not self._use_instance:
            return self._schema()
        return self._schema.clone()

    def empty(self, value):
        if not hasattr(value, '_doc'):
            return True
        if not value._doc or value._doc is None:
            return True
        return False

    def validate(self, value, required=True):
        value.validate(required=required)
        value = super(SchemaProperty, self).validate(value)

        if value is None:
            return Value

        if not isinstance(value, DocumentSchema):
            raise BadValueError(
                'Property %s must be DocumentSchema instance, not a %s' % (self.name, 
                type(value).__name__))
        
        return value

    def _to_python(self, value):
        if not self._use_instance: 
            schema = self._schema()
        else:
            schema = self._schema.clone()
        return schema.wrap(value)

    def _to_json(self, value):
        if not isinstance(value, DocumentSchema):
            if not self._use_instance:
                schema = self._schema()
            else:
                schema = self._schema.clone()

            if not isinstance(value, dict):
                raise BadValueError("%s is not a dict" % str(value))
            value = schema(**value)
        return value._doc

def ListProperty(Property):
    def __init__(self, prop, verbose_name=None, name=None, 
            required=False, validators=None, default=None):
            
        Property.__init__(self, verbose_name=None,
            name=None, required=False, validators=None)
            
        if type(prop) is type:
            if issubclass(prop, Property):
                prop = prop()
            elif issubclass(prop, DocumentSchema):
                prop = SchemaProperty(prop)
        self.prop = prop
        
        
    def validate(self, value, required=True):
        for item in value:
            item.validate()
            
        value = super(ListProperty, self).validate(value)
        if value is None:
            return Value
            
        if not isinstance(value, self.prop.__class__):
            raise BadValueError(
                'Property %s must be %s instance, not a %s' % (self.name, self.prop.__class__.__name__,
                type(value).__name__))
        
        return value
        
    def to_python(self, value):
        return self.ProxyList(value, self.prop)
        
    def _to_json(self, value):
        return [self.prop.to_json(item) for item in value]
        
        
    class ProxyList(list):

        def __init__(self, l, prop):
            self.prop = prop
            list.__init__(self, l)

        def __getitem__(self, index):
            return self.prop._to_python(self[index])

        def __setitem__(self, index, value):
            self[index] = self.prop._to_json(value)

        def append(self, *args, **kwargs):
            if args:
                assert len(args) == 1
                value = args[0]
            else:
                value = kwargs
            value = self.prop._to_json(value)
            super(Proxy, self).append(value)