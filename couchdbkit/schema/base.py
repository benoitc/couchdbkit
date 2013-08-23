# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

""" module that provides a Document object that allows you
to map CouchDB document in Python statically, dynamically or both
"""
import copy

import jsonobject
from jsonobject.exceptions import DeleteNotAllowed
from couchdbkit.utils import ProxyDict
from ..exceptions import ResourceNotFound, ReservedWordError


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


class SchemaProperties(jsonobject.JsonObjectMeta):
    def __new__(mcs, name, bases, dct):
        if isinstance(dct.get('doc_type'), basestring):
            doc_type = dct.pop('doc_type')
        else:
            doc_type = name
        cls = super(SchemaProperties, mcs).__new__(mcs, name, bases, dct)
        cls._doc_type = doc_type
        return cls


class DocumentSchema(jsonobject.JsonObject):

    __metaclass__ = SchemaProperties

    _validate_required_lazily = True

    @jsonobject.StringProperty
    def doc_type(self):
        return self._doc_type

    @property
    def _doc(self):
        return ProxyDict(self, self._obj)

    @property
    def _dynamic_properties(self):
        from jsonobject.base import get_dynamic_properties
        return get_dynamic_properties(self)

    def __delitem__(self, key):
        try:
            super(DocumentSchema, self).__delitem__(key)
        except DeleteNotAllowed:
            self[key] = None

    def __delattr__(self, name):
        try:
            super(DocumentSchema, self).__delattr__(name)
        except DeleteNotAllowed:
            setattr(self, name, None)


class DocumentBase(DocumentSchema):

    _id = jsonobject.StringProperty(exclude_if_none=True)
    _rev = jsonobject.StringProperty(exclude_if_none=True)
    _attachments = jsonobject.DictProperty(exclude_if_none=True)

    _db = None

    # The rest of this class is mostly copied from couchdbkit 0.5.7

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
