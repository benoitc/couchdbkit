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
from calendar import timegm
import datetime
import decimal
import time

import couchdbkit
from couchdbkit.properties import Property
from couchdbkit.properties_map import value_to_json, value_to_python
from couchdbkit.schema import DocumentSchema, ALLOWED_PROPERTY_TYPES
from couchdbkit.exceptions import *


__all__ = ['SchemaProperty', 'ListProperty']

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

    def to_python(self, value):
        if not self._use_instance: 
            schema = self._schema()
        else:
            schema = self._schema.clone()
        return schema.wrap(value)

    def to_json(self, value):
        if not isinstance(value, DocumentSchema):
            if not self._use_instance:
                schema = self._schema()
            else:
                schema = self._schema.clone()

            if not isinstance(value, dict):
                raise BadValueError("%s is not a dict" % str(value))
            value = schema(**value)
        return value._doc
        
       
class ListProperty(Property):
    """A property that stores a list of things.

      """
    def __init__(self, verbose_name=None, default=None, **kwds):
        """Construct ListProperty.

    
         :args verbose_name: Optional verbose name.
         :args default: Optional default value; if omitted, an empty list is used.
         :args**kwds: Optional additional keyword arguments, passed to base class.

        Note that the only permissible value for 'required' is True.
        
        """
        if 'required' in kwds and kwds['required'] is not True:
             raise ValueError('List values must be required')
        if default is None:
            default = []

        Property.__init__(self, verbose_name, default=default,
            required=True, **kwds)
        
    data_type = list
        
    def validate(self, value, required=True):
        value = super(ListProperty, self).validate(value)
        if value is not None:
            if not isinstance(value, list):
                raise BadValueError('Property %s must be a list' % self.name)
            value = self.validate_list_contents(value)
        return value
        
    def validate_list_contents(self, value):
        for item in value:
            if type(item) not in ALLOWED_PROPERTY_TYPES:
                raise BadValueError(
                    'Items in the %s list must all be in ' %
                        (self.name, ALLOWED_PROPERTY_TYPES))
        return value
        
    def empty(self, value):
        """Is list property empty.

        [] is not an empty value.

        Returns:
          True if value is None, else false.
        """
        return value is None
        
    def default_value(self):
        """Default value for list.

        Because the property supplied to 'default' is a static value,
        that value must be shallow copied to prevent all fields with
        default values from sharing the same instance.

        Returns:
          Copy of the default value.
        """
        value = super(ListProperty, self).default_value()
        if value is None:
            value = []
        return list(value)
        
    def to_python(self, value):
        return self.ListProxy(value)
        
    def to_json(self, value):
        return [value_to_json(item) for item in value]

    class ListProxy(list):
        """ ProxyList. Idee taken from couchdb-python."""
        def __init__(self, l):
            self._list = l

        def __lt__(self, other):
            return self._list < other

        def __le__(self, other):
            return self._list <= other

        def __eq__(self, other):
            return self._list == other

        def __ne__(self, other):
            return self._list != other

        def __gt__(self, other):
            return self._list > other

        def __ge__(self, other):
            return self._list >= other

        def __repr__(self):
            return repr(list(self._list))

        def __str__(self):
            return str(self._list)

        def __unicode__(self):
            return unicode(self._list)

        def __delitem__(self, index):
            del self._list[index]

        def __getitem__(self, index):
            return value_to_python(self._list[index])

        def __setitem__(self, index, value):
            self._list[index] = value_to_json(item)

        def __iter__(self):
            for index in range(len(self)):
                yield self[index]

        def __len__(self):
            return len(self._list)

        def __nonzero__(self):
            return bool(self._list)

        def append(self, *args, **kwargs):
            if args:
                assert len(args) == 1
                value = args[0]
            else:
                value = kwargs
            value = value_to_json(value)
            self._list.append(value)

        def extend(self, list):
            for item in list:
                self.append(item)