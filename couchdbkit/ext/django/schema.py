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
import re
import sys

from django.conf import settings
from django.db.models.options import get_verbose_name
from django.utils.translation import activate, deactivate_all, get_language, \
string_concat
from django.utils.encoding import smart_str, force_unicode

from couchdbkit import schema
from couchdbkit.ext.django.loading import get_schema, register_schema, \
get_db

__all__ = ['Property', 'StringProperty', 'IntegerProperty',
            'DecimalProperty', 'BooleanProperty', 'FloatProperty',
            'DateTimeProperty', 'DateProperty', 'TimeProperty',
            'dict_to_json', 'list_to_json', 'value_to_json',
            'value_to_python', 'dict_to_python', 'list_to_python',
            'convert_property', 'DocumentSchema', 'Document',
            'SchemaProperty', 'SchemaListProperty', 'ListProperty',
            'DictProperty', 'StringListProperty', 'SchemaDictProperty',
            'SetProperty',]


DEFAULT_NAMES = ('verbose_name', 'db_table', 'ordering',
                 'app_label')

class Options(object):
    """ class based on django.db.models.options. We only keep
    useful bits."""

    def __init__(self, meta, app_label=None):
        self.module_name, self.verbose_name = None, None
        self.verbose_name_plural = None
        self.object_name, self.app_label = None, app_label
        self.meta = meta
        self.admin = None

    def contribute_to_class(self, cls, name):
        cls._meta = self
        self.installed = re.sub('\.models$', '', cls.__module__) in settings.INSTALLED_APPS
        # First, construct the default values for these options.
        self.object_name = cls.__name__
        self.module_name = self.object_name.lower()
        self.verbose_name = get_verbose_name(self.object_name)

        # Next, apply any overridden values from 'class Meta'.
        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                # Ignore any private attributes that Django doesn't care about.
                # NOTE: We can't modify a dictionary's contents while looping
                # over it, so we loop over the *original* dictionary instead.
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))

            # verbose_name_plural is a special case because it uses a 's'
            # by default.
            setattr(self, 'verbose_name_plural', meta_attrs.pop('verbose_name_plural', string_concat(self.verbose_name, 's')))

            # Any leftover attributes must be invalid.
            if meta_attrs != {}:
                raise TypeError("'class Meta' got invalid attribute(s): %s" % ','.join(meta_attrs.keys()))
        else:
            self.verbose_name_plural = string_concat(self.verbose_name, 's')
        del self.meta

    def __str__(self):
        return "%s.%s" % (smart_str(self.app_label), smart_str(self.module_name))

    def verbose_name_raw(self):
        """
        There are a few places where the untranslated verbose name is needed
        (so that we get the same value regardless of currently active
        locale).
        """
        lang = get_language()
        deactivate_all()
        raw = force_unicode(self.verbose_name)
        activate(lang)
        return raw
    verbose_name_raw = property(verbose_name_raw)

class DocumentMeta(schema.SchemaProperties):
    def __new__(cls, name, bases, attrs):
        super_new = super(DocumentMeta, cls).__new__
        parents = [b for b in bases if isinstance(b, DocumentMeta)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        new_class = super_new(cls, name, bases, attrs)
        attr_meta = attrs.pop('Meta', None)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta

        if getattr(meta, 'app_label', None) is None:
            document_module = sys.modules[new_class.__module__]
            app_label = document_module.__name__.split('.')[-2]
        else:
            app_label = getattr(meta, 'app_label')

        new_class.add_to_class('_meta', Options(meta, app_label=app_label))

        register_schema(app_label, new_class)

        return get_schema(app_label, name)

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

class Document(schema.Document):
    """ Document object for django extension """
    __metaclass__ = DocumentMeta

    get_id = property(lambda self: self['_id'])
    get_rev = property(lambda self: self['_rev'])

    @classmethod
    def get_db(cls):
        db = getattr(cls, '_db', None)
        if db is None:
            app_label = getattr(cls._meta, "app_label")
            db = get_db(app_label)
            cls._db = db
        return db

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
SchemaListProperty = schema.SchemaListProperty
ListProperty = schema.ListProperty
DictProperty = schema.DictProperty
StringListProperty = schema.StringListProperty
SchemaDictProperty = schema.SchemaDictProperty
SetProperty = schema.SetProperty



# some utilities
dict_to_json = schema.dict_to_json
list_to_json = schema.list_to_json
value_to_json = schema.value_to_json
value_to_python = schema.value_to_python
dict_to_python = schema.dict_to_python
list_to_python = schema.list_to_python
convert_property = schema.convert_property
