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

""" Wrapper of couchdbkit Document and Properties for django. It also 
add possibility to a document to register itself in CouchdbkitHandler
"""

import sys

from couchdbkit import schema
from couchdbkit.ext.django.loading import get_schema, register_schema

__all__ = ['Property', 'StringProperty', 'IntegerProperty', 
            'DecimalProperty', 'BooleanProperty', 'FloatProperty', 
            'DateTimeProperty', 'DateProperty', 'TimeProperty', 
            'dict_to_json', 'list_to_json', 'value_to_json', 
            'value_to_python', 'dict_to_python', 'list_to_python', 
            'convert_property', 'DocumentSchema', 'Document', 
            'SchemaProperty', 'ListProperty', 
            'DictProperty', 'StringListProperty']

class DocumentMeta(schema.SchemaProperties):
    def __new__(cls, name, bases, attrs):
        super_new = super(DocumentMeta, cls).__new__
        parents = [b for b in bases if isinstance(b, DocumentMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)
            
        new_class = super_new(cls, name, bases, attrs)
        document_module = sys.modules[new_class.__module__]
        app_label = document_module.__name__.split('.')[-2]
        register_schema(app_label, new_class)
        
        return get_schema(app_label, name)

class Document(schema.Document):
    """ Document object for django extension """
    __metaclass__ = DocumentMeta
    
    get_id = property(lambda self: self['_id'])
    get_rev = property(lambda self: self['_rev'])
    
    
DocumentSchema = schema.DocumentSchema    

#  properties
Property = schema.Property
StringProperty = schema.StringProperty
IntegerProperty = schema.IntegerProperty
DecimalProperty = schema.DecimalProperty
BooleanProperty = schema.BooleanProperty
FloatProperty = schema.FloatProperty
DateTimeProperty = schema.DateTimeProperty
DateProperty = schema.DateProperty
TimeProperty = schema.TimeProperty
SchemaProperty = schema.SchemaProperty
ListProperty = schema.ListProperty
DictProperty = schema.DictProperty
StringListProperty = schema.StringListProperty


# some utilities
dict_to_json = schema.dict_to_json
list_to_json = schema.list_to_json
value_to_json = schema.value_to_json
value_to_python = schema.value_to_python
dict_to_python = schema.dict_to_python
list_to_python = schema.list_to_python
convert_property = schema.convert_property
