# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

""" module that provides a Document object that allows you
to map CouchDB document in Python statically, dynamically or both
"""


from . import properties as p
from .properties import value_to_python, \
convert_property, MAP_TYPES_PROPERTIES, ALLOWED_PROPERTY_TYPES, \
LazyDict, LazyList
from ..exceptions import DuplicatePropertyError, ResourceNotFound, \
ReservedWordError 


__all__ = ['ReservedWordError', 'ALLOWED_PROPERTY_TYPES', 'DocumentSchema',
        'SchemaProperties', 'DocumentBase', 'QueryMixin', 'AttachmentMixin',
        'Document', 'StaticDocument', 'valid_id']

_RESERVED_WORDS = ['_id', '_rev', '$schema']

_NODOC_WORDS = ['doc_type']

def check_reserved_words(attr_name):
    if attr_name in _RESERVED_WORDS:
        raise ReservedWordError(
            "Cannot define property using reserved word '%(attr_name)s'." %
            locals())

def valid_id(value):
    if isinstance(value, basestring) and not value.startswith('_'):
        return value
    raise TypeError('id "%s" is invalid' % value)

class SchemaProperties(type):

    def __new__(cls, name, bases, attrs):
        # init properties
        properties = {}
        defined = set()
        for base in bases:
            if hasattr(base, '_properties'):
                property_keys = base._properties.keys()
                duplicate_properties = defined.intersection(property_keys)
                if duplicate_properties:
                    raise DuplicatePropertyError(
                        'Duplicate properties in base class %s already defined: %s' % (base.__name__, list(duplicate_properties)))
                defined.update(property_keys)
                properties.update(base._properties)

        doc_type = attrs.get('doc_type', False)
        if not doc_type:
            doc_type = name
        else:
            del attrs['doc_type']

        attrs['_doc_type'] = doc_type

        for attr_name, attr in attrs.items():
            # map properties
            if isinstance(attr, p.Property):
                check_reserved_words(attr_name)
                if attr_name in defined:
                    raise DuplicatePropertyError('Duplicate property: %s' % attr_name)
                properties[attr_name] = attr
                attr.__property_config__(cls, attr_name)
            # python types
            elif type(attr) in MAP_TYPES_PROPERTIES and \
                    not attr_name.startswith('_') and \
                    attr_name not in _NODOC_WORDS:
                check_reserved_words(attr_name)
                if attr_name in defined:
                    raise DuplicatePropertyError('Duplicate property: %s' % attr_name)
                prop = MAP_TYPES_PROPERTIES[type(attr)](default=attr)
                properties[attr_name] = prop
                prop.__property_config__(cls, attr_name)
                attrs[attr_name] = prop

        attrs['_properties'] = properties
        return type.__new__(cls, name, bases, attrs)


class DocumentSchema(object):
    __metaclass__ = SchemaProperties

    _dynamic_properties = None
    _allow_dynamic_properties = True
    _doc = None
    _db = None

    def __init__(self, _d=None, **properties):
        self._dynamic_properties = {}
        self._doc = {}

        if _d is not None:
            if not isinstance(_d, dict):
                raise TypeError('d should be a dict')
            properties.update(_d)

        doc_type = getattr(self, '_doc_type', self.__class__.__name__)
        self._doc['doc_type'] = doc_type
        
        for prop in self._properties.values():
            if prop.name in properties:
                value = properties.pop(prop.name)
                if value is None:
                    value = prop.default_value()
            else:
                value = prop.default_value()
            prop.__property_init__(self, value)
            self.__dict__[prop.name] = value

        _dynamic_properties = properties.copy()
        for attr_name, value in _dynamic_properties.iteritems():
            if attr_name not in self._properties \
                    and value is not None:
                if isinstance(value, p.Property):
                    value.__property_config__(self, attr_name)
                    value.__property_init__(self, value.default_value())
                elif isinstance(value, DocumentSchema):
                    from couchdbkit.schema import SchemaProperty
                    value = SchemaProperty(value)
                    value.__property_config__(self, attr_name)
                    value.__property_init__(self, value.default_value())


                setattr(self, attr_name, value)
                # remove the kwargs to speed stuff
                del properties[attr_name]

    def dynamic_properties(self):
        """ get dict of dynamic properties """
        if self._dynamic_properties is None:
            return {}
        return self._dynamic_properties.copy()

    @classmethod
    def properties(cls):
        """ get dict of defined properties """
        return cls._properties.copy()

    def all_properties(self):
        """ get all properties.
        Generally we just need to use keys"""
        all_properties = self._properties.copy()
        all_properties.update(self.dynamic_properties())
        return all_properties

    def to_json(self):
        if self._doc.get('doc_type') is None:
            doc_type = getattr(self, '_doc_type', self.__class__.__name__)
            self._doc['doc_type'] = doc_type
        return self._doc

    #TODO: add a way to maintain custom dynamic properties
    def __setattr__(self, key, value):
        """
        override __setattr__ . If value is in dir, we just use setattr.
        If value is not known (dynamic) we test if type and name of value
        is supported (in ALLOWED_PROPERTY_TYPES, Property instance and not
        start with '_') a,d add it to `_dynamic_properties` dict. If value is
        a list or a dict we use LazyList and LazyDict to maintain in the value.
        """

        if key == "_id" and valid_id(value):
            self._doc['_id'] = value
        elif key == "_deleted":
            self._doc["_deleted"] = value
        elif key == "_attachments":
            if key not in self._doc or not value:
                self._doc[key] = {}
            elif not isinstance(self._doc[key], dict):
                self._doc[key] = {}
            value = LazyDict(self._doc[key], init_vals=value)
        else:
            check_reserved_words(key)
            if not hasattr( self, key ) and not self._allow_dynamic_properties:
                raise AttributeError("%s is not defined in schema (not a valid property)" % key)

            elif not key.startswith('_') and \
                    key not in self.properties() and \
                    key not in dir(self):
                if type(value) not in ALLOWED_PROPERTY_TYPES and \
                        not isinstance(value, (p.Property,)):
                    raise TypeError("Document Schema cannot accept values of type '%s'." %
                            type(value).__name__)

                if self._dynamic_properties is None:
                    self._dynamic_properties = {}

                if isinstance(value, dict):
                    if key not in self._doc or not value:
                        self._doc[key] = {}
                    elif not isinstance(self._doc[key], dict):
                        self._doc[key] = {}
                    value = LazyDict(self._doc[key], init_vals=value)
                elif isinstance(value, list):
                    if key not in self._doc or not value:
                        self._doc[key] = []
                    elif not isinstance(self._doc[key], list):
                        self._doc[key] = []
                    value = LazyList(self._doc[key], init_vals=value)

                self._dynamic_properties[key] = value

                if not isinstance(value, (p.Property,)) and \
                        not isinstance(value, dict) and \
                        not isinstance(value, list):
                    if callable(value):
                        value = value()
                    self._doc[key] = convert_property(value)
            else:
                object.__setattr__(self, key, value)

    def __delattr__(self, key):
        """ delete property
        """
        if key in self._doc:
            del self._doc[key]

        if self._dynamic_properties and key in self._dynamic_properties:
            del self._dynamic_properties[key]
        else:
            object.__delattr__(self, key)

    def __getattr__(self, key):
        """ get property value
        """
        if self._dynamic_properties and key in self._dynamic_properties:
            return self._dynamic_properties[key]
        elif key  in ('_id', '_rev', '_attachments', 'doc_type'):
            return self._doc.get(key)
        try:
            return self.__dict__[key]
        except KeyError, e:
            raise AttributeError(e)

    def __getitem__(self, key):
        """ get property value
        """
        try:
            attr = getattr(self, key)
            if callable(attr):
                raise AttributeError("existing instance method")
            return attr
        except AttributeError:
            if key in self._doc:
                return self._doc[key]
            raise

    def __setitem__(self, key, value):
        """ add a property
        """
        setattr(self, key, value)


    def __delitem__(self, key):
        """ delete a property
        """
        try:
            delattr(self, key)
        except AttributeError, e:
            raise KeyError, e


    def __contains__(self, key):
        """ does object contain this propery ?

        @param key: name of property

        @return: True if key exist.
        """
        if key in self.all_properties():
            return True
        elif key in self._doc:
            return True
        return False

    def __iter__(self):
        """ iter document instance properties
        """
        for k in self.all_properties().keys():
            yield k, self[k]
        raise StopIteration

    iteritems = __iter__

    def items(self):
        """ return list of items
        """
        return [(k, self[k]) for k in self.all_properties().keys()]


    def __len__(self):
        """ get number of properties
        """
        return len(self._doc or ())

    def __getstate__(self):
        """ let pickle play with us """
        obj_dict = self.__dict__.copy()
        return obj_dict

    @classmethod
    def wrap(cls, data):
        """ wrap `data` dict in object properties """
        instance = cls()
        instance._doc = data
        for prop in instance._properties.values():
            if prop.name in data:
                value = data[prop.name]
                if value is not None:
                    value = prop.to_python(value)
                else:
                    value = prop.default_value()
            else:
                value = prop.default_value()
            prop.__property_init__(instance, value)

        if cls._allow_dynamic_properties:
            for attr_name, value in data.iteritems():
                if attr_name in instance.properties():
                    continue
                if value is None:
                    continue
                elif attr_name.startswith('_'):
                    continue
                elif attr_name == 'doc_type':
                    continue
                else:
                    value = value_to_python(value)
                    setattr(instance, attr_name, value)
        return instance
    from_json = wrap

    def validate(self, required=True):
        """ validate a document """
        for attr_name, value in self._doc.items():
            if attr_name in self._properties:
                self._properties[attr_name].validate(
                        getattr(self, attr_name), required=required)
        return True

    def clone(self, **kwargs):
        """ clone a document """
        kwargs.update(self._dynamic_properties)
        obj = self.__class__(**kwargs)
        obj._doc = self._doc
        return obj

    @classmethod
    def build(cls, **kwargs):
        """ build a new instance from this document object. """
        properties = {}
        for attr_name, attr in kwargs.items():
            if isinstance(attr, (p.Property,)):
                properties[attr_name] = attr
                attr.__property_config__(cls, attr_name)
            elif type(attr) in MAP_TYPES_PROPERTIES and \
                    not attr_name.startswith('_') and \
                    attr_name not in _NODOC_WORDS:
                check_reserved_words(attr_name)

                prop = MAP_TYPES_PROPERTIES[type(attr)](default=attr)
                properties[attr_name] = prop
                prop.__property_config__(cls, attr_name)
                properties[attr_name] = prop
        return type('AnonymousSchema', (cls,), properties)

class DocumentBase(DocumentSchema):
    """ Base Document object that map a CouchDB Document.
    It allow you to statically map a document by
    providing fields like you do with any ORM or
    dynamically. Ie unknown fields are loaded as
    object property that you can edit, datetime in
    iso3339 format are automatically translated in
    python types (date, time & datetime) and decimal too.

    Example of documentass

    .. code-block:: python

        from couchdbkit.schema import *
        class MyDocument(Document):
            mystring = StringProperty()
            myotherstring = unicode() # just use python types


    Document fields can be accessed as property or
    key of dict. These are similar : ``value = instance.key or value = instance['key'].``

    To delete a property simply do ``del instance[key'] or delattr(instance, key)``
    """
    _db = None

    def __init__(self, _d=None, **kwargs):
        _d = _d or {}
        
        docid = kwargs.pop('_id', _d.pop("_id", ""))
        docrev = kwargs.pop('_rev', _d.pop("_rev", ""))
        
        DocumentSchema.__init__(self, _d, **kwargs)
        
        if docid: self._doc['_id'] = valid_id(docid)
        if docrev: self._doc['_rev'] = docrev            

    @classmethod
    def set_db(cls, db):
        """ Set document db"""
        cls._db = db

    @classmethod
    def get_db(cls):
        """ get document db"""
        db = getattr(cls, '_db', None)
        if db is None:
            raise TypeError("doc database required to save document")
        return db

    def save(self, **params):
        """ Save document in database.

        @params db: couchdbkit.core.Database instance
        """
        self.validate()
        db = self.get_db()

        doc = self.to_json()
        db.save_doc(doc, **params)
        if '_id' in doc and '_rev' in doc:
            self._doc.update(doc)
        elif '_id' in doc:
            self._doc.update({'_id': doc['_id']})

    store = save

    @classmethod
    def save_docs(cls, docs, use_uuids=True, all_or_nothing=False):
        """ Save multiple documents in database.

        @params docs: list of couchdbkit.schema.Document instance
        @param use_uuids: add _id in doc who don't have it already set.
        @param all_or_nothing: In the case of a power failure, when the database
        restarts either all the changes will have been saved or none of them.
        However, it does not do conflict checking, so the documents will
        be committed even if this creates conflicts.

        """
        db = cls.get_db()
        docs_to_save= [doc for doc in docs if doc._doc_type == cls._doc_type]
        if not len(docs_to_save) == len(docs):
            raise ValueError("one of your documents does not have the correct type")
        db.bulk_save(docs_to_save, use_uuids=use_uuids, all_or_nothing=all_or_nothing)

    bulk_save = save_docs

    @classmethod
    def get(cls, docid, rev=None, db=None, dynamic_properties=True):
        """ get document with `docid`
        """
        if not db:
            db = cls.get_db()
        cls._allow_dynamic_properties = dynamic_properties
        return db.get(docid, rev=rev, wrapper=cls.wrap)

    @classmethod
    def get_or_create(cls, docid=None, db=None, dynamic_properties=True, **params):
        """ get  or create document with `docid` """
       
        if db:
            cls.set_db(db)
        cls._allow_dynamic_properties = dynamic_properties
        db = cls.get_db()

        if docid is None:
            obj = cls()
            obj.save(**params)
            return obj

        rev = params.pop('rev', None)

        try:
            return db.get(docid, rev=rev, wrapper=cls.wrap, **params)
        except ResourceNotFound:
            obj = cls()
            obj._id = docid
            obj.save(**params)
            return obj

    new_document = property(lambda self: self._doc.get('_rev') is None)

    def delete(self):
        """ Delete document from the database.
        @params db: couchdbkit.core.Database instance
        """
        if self.new_document:
            raise TypeError("the document is not saved")
        
        db = self.get_db()
        
        # delete doc
        db.delete_doc(self._id)

        # reinit document
        del self._doc['_id']
        del self._doc['_rev']

class AttachmentMixin(object):
    """
    mixin to manage doc attachments.

    """

    def put_attachment(self, content, name=None, content_type=None,
                content_length=None):
        """ Add attachement to a document.

        @param content: string or :obj:`File` object.
        @param name: name or attachment (file name).
        @param content_type: string, mimetype of attachment.
        If you don't set it, it will be autodetected.
        @param content_lenght: int, size of attachment.

        @return: bool, True if everything was ok.
        """
        db = self.get_db() 
        return db.put_attachment(self._doc, content, name=name,
            content_type=content_type, content_length=content_length)

    def delete_attachment(self, name):
        """ delete document attachment

        @param name: name of attachment

        @return: dict, with member ok set to True if delete was ok.
        """

        db = self.get_db()
        result = db.delete_attachment(self._doc, name)
        try:
            self._doc['_attachments'].pop(name)
        except KeyError:
            pass
        return result

    def fetch_attachment(self, name, stream=False):
        """ get attachment in a adocument

        @param name: name of attachment default: default result
        @param stream: boolean, response return a ResponseStream object
        @param stream_size: int, size in bytes of response stream block

        @return: str or unicode, attachment
        """
        db = self.get_db()
        return db.fetch_attachment(self._doc, name, stream=stream)


class QueryMixin(object):
    """ Mixin that add query methods """

    @classmethod
    def __view(cl, view_type=None, data=None, wrapper=None,
    dynamic_properties=True, wrap_doc=True, classes=None, **params):
        """
        The default wrapper can distinguish between multiple Document
        classes and wrap the result accordingly. The known classes are
        passed either as classes={<doc_type>: <Document-class>, ...} or
        classes=[<Document-class1>, <Document-class2>, ...]
        """

        def default_wrapper(row):
            data = row.get('value')
            docid = row.get('id')
            doc = row.get('doc')
            if doc is not None and wrap_doc:
                cls = classes.get(doc.get('doc_type')) if classes else cl
                cls._allow_dynamic_properties = dynamic_properties
                return cls.wrap(doc)

            elif not data or data is None:
                return row
            elif not isinstance(data, dict) or not docid:
                return row
            else:
                cls = classes.get(data.get('doc_type')) if classes else cl
                data['_id'] = docid
                if 'rev' in data:
                    data['_rev'] = data.pop('rev')
                cls._allow_dynamic_properties = dynamic_properties
                return cls.wrap(data)

        if isinstance(classes, list):
            classes = dict([(c._doc_type, c) for c in classes])

        if wrapper is None:
            wrapper = default_wrapper

        if not wrapper:
            wrapper = None
        elif not callable(wrapper):
            raise TypeError("wrapper is not a callable")

        db = cl.get_db()
        if view_type == 'view':
            return db.view(data, wrapper=wrapper, **params)
        elif view_type == 'temp_view':
            return db.temp_view(data, wrapper=wrapper, **params)
        else:
            raise RuntimeError("bad view_type : %s" % view_type )

    @classmethod
    def view(cls, view_name, wrapper=None, dynamic_properties=True,
    wrap_doc=True, classes=None, **params):
        """ Get documents associated view a view.
        Results of view are automatically wrapped
        to Document object.

        @params view_name: str, name of view
        @params wrapper: override default wrapper by your own
        @dynamic_properties: do we handle properties which aren't in
        the schema ? Default is True.
        @wrap_doc: If True, if a doc is present in the row it will be
        used for wrapping. Default is True.
        @params params:  params of view

        @return: :class:`simplecouchdb.core.ViewResults` instance. All
        results are wrapped to current document instance.
        """
        return cls.__view(view_type="view", data=view_name, wrapper=wrapper,
            dynamic_properties=dynamic_properties, wrap_doc=wrap_doc,
            classes=classes, **params)

    @classmethod
    def temp_view(cls, design, wrapper=None, dynamic_properties=True,
    wrap_doc=True, classes=None, **params):
        """ Slow view. Like in view method,
        results are automatically wrapped to
        Document object.

        @params design: design object, See `simplecouchd.client.Database`
        @dynamic_properties: do we handle properties which aren't in
            the schema ?
        @wrap_doc: If True, if a doc is present in the row it will be
            used for wrapping. Default is True.
        @params params:  params of view

        @return: Like view, return a :class:`simplecouchdb.core.ViewResults`
        instance. All results are wrapped to current document instance.
        """
        return cls.__view(view_type="temp_view", data=design, wrapper=wrapper,
            dynamic_properties=dynamic_properties, wrap_doc=wrap_doc,
            classes=classes, **params)

class Document(DocumentBase, QueryMixin, AttachmentMixin):
    """
    Full featured document object implementing the following :

    :class:`QueryMixin` for view & temp_view that wrap results to this object
    :class `AttachmentMixin` for attachments function
    """

class StaticDocument(Document):
    """
    Shorthand for a document that disallow dynamic properties.
    """
    _allow_dynamic_properties = False
