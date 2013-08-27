# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.
import functools
from jsonobject.properties import *
from jsonobject.base import DefaultProperty
from jsonobject.convert import ALLOWED_PROPERTY_TYPES

SchemaProperty = ObjectProperty
SchemaListProperty = ListProperty
StringListProperty = functools.partial(ListProperty, unicode)
SchemaDictProperty = DictProperty


class Property(DefaultProperty):
    def wrap(self, obj):
        try:
            return self.to_python(obj)
        except NotImplementedError:
            return super(Property, self).wrap(obj)

    def unwrap(self, obj):
        try:
            return obj, self.to_json(obj)
        except NotImplementedError:
            return super(Property, self).unwrap(obj)

    def to_python(self, value):
        raise NotImplementedError()

    def to_json(self, value):
        raise NotImplementedError()


dict_to_json = None
list_to_json = None
value_to_json = None
value_to_python = None
dict_to_python = None
list_to_python = None
convert_property = None
value_to_property = None

LazyDict = JsonDict
LazyList = JsonArray
LazySet = JsonSet
