# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.
import functools
from jsonobject.properties import *
from jsonobject.base import DefaultProperty
from jsonobject.convert import (
    ALLOWED_PROPERTY_TYPES,
    MAP_TYPES_PROPERTIES,
    value_to_python,
    value_to_property
)

StringListProperty = functools.partial(ListProperty, unicode)


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


def _not_implemented(*args, **kwargs):
    raise NotImplementedError()

dict_to_json = _not_implemented
list_to_json = _not_implemented
value_to_json = _not_implemented
dict_to_python = _not_implemented
list_to_python = _not_implemented
convert_property = _not_implemented

LazyDict = JsonDict
LazyList = JsonArray
LazySet = JsonSet
