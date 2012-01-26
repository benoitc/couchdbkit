# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

""" Meta properties """


from ..exceptions import BadValueError 

from .base import DocumentSchema
from .properties import Property

__all__ = ['SchemaProperty', 'SchemaListProperty', 'SchemaDictProperty']

class SchemaProperty(Property):
    """ Schema property. It allows you add a DocumentSchema instance 
    a member of a Document object. It returns a
   `schemaDocumentSchema` object.

    Exemple :
    
            >>> from couchdbkit import *
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
            >>> from couchdbkit import Server
            >>> s = Server()
            >>> db = s.create_db('couchdbkit_test')
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
            name=None, required=False, validators=None, default=default)
       
        use_instance = True
        if isinstance(schema, type):
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
            if self.default:
                return self.default
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
            return value

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

        if not self._use_instance:
            schema = self._schema
        else:
            schema = self._schema.__class__
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

class SchemaListProperty(Property):
    """A property that stores a list of things.

      """
    def __init__(self, schema, verbose_name=None, default=None, 
            required=False, **kwds):
        
        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)
    
        use_instance = True
        if isinstance(schema, type):
            use_instance = False    

        elif not isinstance(schema, DocumentSchema):
            raise TypeError('schema should be a DocumentSchema instance')
       
        elif schema.__class__.__name__ == 'DocumentSchema':
            use_instance = False
            properties = schema._dynamic_properties.copy()
            schema = DocumentSchema.build(**properties)
            
        self._use_instance = use_instance
        self._schema = schema
        
    def validate(self, value, required=True):
        value = super(SchemaListProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, list):
                raise BadValueError('Property %s must be a list' % self.name)
            value = self.validate_list_schema(value, required=required)
        return value
        
    def validate_list_schema(self, value, required=True):
        for v in value:
             v.validate(required=required)
        return value
        
    def default_value(self):
        return []
        
    def to_python(self, value):
        return LazySchemaList(value, self._schema, self._use_instance)
        
    def to_json(self, value):
        return [svalue_to_json(v, self._schema, self._use_instance) for v in value]
        
        
class LazySchemaList(list):

    def __init__(self, doc, schema, use_instance, init_vals=None):
        list.__init__(self)
        
        self.schema = schema
        self.use_instance = use_instance
        self.doc = doc
        if init_vals is None:
            # just wrap the current values
            self._wrap()
        else:
            # initialize this list and the underlying list
            # with the values given.
            del self.doc[:]
            for item in init_vals:
                self.append(item)

    def _wrap(self):
        for v in self.doc:
            if not self.use_instance: 
                schema = self.schema()
            else:
                schema = self.schema.clone()
                
            value = schema.wrap(v)
            list.append(self, value)

    def __delitem__(self, index):
        del self.doc[index]
        list.__delitem__(self, index)

    def __setitem__(self, index, value):
        self.doc[index] = svalue_to_json(value, self.schema, 
                                    self.use_instance)
        list.__setitem__(self, index, value)

    def __delslice__(self, i, j):
        del self.doc[i:j]
        super(LazySchemaList, self).__delslice__(i, j)

    def __getslice__(self, i, j):
        return LazySchemaList(self.doc[i:j], self.schema, self.use_instance)

    def __setslice__(self, i, j, seq):
        self.doc[i:j] = (svalue_to_json(v, self.schema, self.use_instance)
                         for v in seq)
        super(LazySchemaList, self).__setslice__(i, j, seq)

    def __contains__(self, value):
        for item in self.doc:
            if item == value._doc:
                return True
        return False

    def append(self, *args, **kwargs):
        if args:
            assert len(args) == 1
            value = args[0]
        else:
            value = kwargs

        self.doc.append(svalue_to_json(value, self.schema, 
                                    self.use_instance))
        super(LazySchemaList, self).append(value)

    def count(self, value):
        return sum(1 for item in self.doc if item == value._doc)

    def extend(self, x):
        self.doc.extend([svalue_to_json(item, self.schema, self.use_instance)
                         for item in x])
        super(LazySchemaList, self).extend(x)

    def index(self, value, *args):
        try:
            i = max(0, args[0])
        except IndexError:
            i = 0
        try:
            j = min(len(self.doc), args[1])
        except IndexError:
            j = len(self.doc)
        if j < 0:
            j += len(self.doc)
        for idx, item in enumerate(self.doc[i:j]):
            if item == value._doc:
                return idx + i
        else:
            raise ValueError('list.index(x): x not in list')

    def insert(self, index, value):
        self.__setslice__(index, index, [value])

    def pop(self, index=-1):
        del self.doc[index]
        return super(LazySchemaList, self).pop(index)

    def remove(self, value):
        try:
            del self[self.index(value)]
        except ValueError:
            raise ValueError('list.remove(x): x not in list')

    def reverse(self):
        self.doc.reverse()
        list.reverse(self)

    def sort(self, cmp=None, key=None, reverse=False):
        self.doc.sort(cmp, key, reverse)
        list.sort(self, cmp, key, reverse)
        
        
class SchemaDictProperty(Property):
    """A property that stores a dict of things.

      """
    def __init__(self, schema, verbose_name=None, default=None,
            required=False, **kwds):

        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)

        use_instance = True
        if isinstance(schema, type):
            use_instance = False

        elif not isinstance(schema, DocumentSchema):
            raise TypeError('schema should be a DocumentSchema instance')

        elif schema.__class__.__name__ == 'DocumentSchema':
            use_instance = False
            properties = schema._dynamic_properties.copy()
            schema = DocumentSchema.build(**properties)

        self._use_instance = use_instance
        self._schema = schema

    def validate(self, value, required=True):
        value = super(SchemaDictProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, dict):
                raise BadValueError('Property %s must be a dict' % self.name)
            value = self.validate_dict_schema(value, required=required)
        return value

    def validate_dict_schema(self, value, required=True):
        for v in value.values():
             v.validate(required=required)
        return value

    def default_value(self):
        return {}

    def to_python(self, value):
        return LazySchemaDict(value, self._schema, self._use_instance)

    def to_json(self, value):
        return dict([(k, svalue_to_json(v, self._schema, self._use_instance)) for k, v in value.items()])


class LazySchemaDict(dict):

    def __init__(self, doc, schema, use_instance, init_vals=None):
        dict.__init__(self)

        self.schema = schema
        self.use_instance = use_instance
        self.doc = doc
        if init_vals is None:
            # just wrap the current values
            self._wrap()
        else:
            # initialize this dict and the underlying dict
            # with the values given.
            del self.doc[:]
            for k, v in init_vals:
                self[k] = self._wrap(v)

    def _wrap(self):
        for k, v in self.doc.items():
            if not self.use_instance:
                schema = self.schema()
            else:
                schema = self.schema.clone()

            value = schema.wrap(v)
            dict.__setitem__(self, k, value)

    def __delitem__(self, index):
        index = str(index)
        del self.doc[index]
        dict.__delitem__(self, index)

    def __getitem__(self, index):
        index = str(index)
        return dict.__getitem__(self, index)

    def __setitem__(self, index, value):
        index = str(index)
        self.doc[index] = svalue_to_json(value, self.schema,
                                    self.use_instance)
        dict.__setitem__(self, index, value)

        
def svalue_to_json(value, schema, use_instance):
    if not isinstance(value, DocumentSchema):
        if not use_instance:
            schema = schema()
        else:
            schema = schema.clone()

        if not isinstance(value, dict):
            raise BadValueError("%s is not a dict" % str(value))
        value = schema(**value)
    return value._doc
