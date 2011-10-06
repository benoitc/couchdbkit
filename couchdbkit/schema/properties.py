# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

""" properties used by Document object """

import decimal
import datetime
import re
import time

try:
    from collections import MutableSet, Iterable

    def is_iterable(c):
        return isinstance(c, Iterable)
except ImportError:
    from sets import Set as MutableSet
    
    def is_iterable(o):
        return hasattr(c, '__iter__')

from couchdbkit.exceptions import BadValueError 

__all__ = ['ALLOWED_PROPERTY_TYPES', 'Property', 'StringProperty',
        'IntegerProperty', 'DecimalProperty', 'BooleanProperty',
        'FloatProperty', 'DateTimeProperty', 'DateProperty',
        'TimeProperty', 'DictProperty', 'ListProperty',
        'StringListProperty', 'SetProperty',
        'dict_to_json', 'list_to_json',
        'value_to_json', 'MAP_TYPES_PROPERTIES', 'value_to_python',
        'dict_to_python', 'list_to_python', 'convert_property',
        'value_to_property', 'LazyDict', 'LazyList', 'LazySet']

ALLOWED_PROPERTY_TYPES = set([
    basestring,
    str,
    unicode,
    bool,
    int,
    long,
    float,
    datetime.datetime,
    datetime.date,
    datetime.time,
    decimal.Decimal,
    dict,
    list,
    set,
    type(None)
])

re_date = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$')
re_time = re.compile('^([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?$')
re_datetime = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])(\D?([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?([zZ]|([\+-])([01]\d|2[0-3])\D?([0-5]\d)?)?)?$')
re_decimal = re.compile('^(\d+)\.(\d+)$')

class Property(object):
    """ Property base which all other properties
    inherit."""
    creation_counter = 0

    def __init__(self, verbose_name=None, name=None,
            default=None, required=False, validators=None,
            choices=None):
        """ Default constructor for a property. 

        :param verbose_name: str, verbose name of field, could
                be use for description
        :param name: str, name of field
        :param default: default value
        :param required: True if field is required, default is False
        :param validators: list of callable or callable, field validators 
        function that are executed when document is saved.
        """
        self.verbose_name = verbose_name
        self.name = name
        self.default = default
        self.required = required
        self.validators = validators
        self.choices = choices
        self.creation_counter = Property.creation_counter
        Property.creation_counter += 1

    def __property_config__(self, document_class, property_name):
        self.document_class = document_class
        if self.name is None:
            self.name = property_name

    def __property_init__(self, document_instance, value):
        """ method used to set value of the property when
        we create the document. Don't check required. """
        if value is not None:
            value = self.to_json(self.validate(value, required=False))
        document_instance._doc[self.name] = value

    def __get__(self, document_instance, document_class):
        if document_instance is None:
            return self

        value = document_instance._doc.get(self.name)
        if value is not None:
            value = self._to_python(value)

        return value

    def __set__(self, document_instance, value):
        value = self.validate(value, required=False)
        document_instance._doc[self.name] = self._to_json(value)

    def __delete__(self, document_instance):
        pass

    def default_value(self):
        """ return default value """

        default = self.default
        if callable(default):
            default = default()
        return default

    def validate(self, value, required=True):
        """ validate value """
        if required and self.empty(value):
            if self.required:
                raise BadValueError("Property %s is required." % self.name)
        else:
            if self.choices and value is not None:
                if isinstance(self.choices, list):      choice_list = self.choices
                if isinstance(self.choices, dict):      choice_list = self.choices.keys()
                if isinstance(self.choices, tuple):     choice_list = [key for (key, name) in self.choices]

                if value not in choice_list:
                    raise BadValueError('Property %s is %r; must be one of %r' % (
                        self.name, value, choice_list))
        if self.validators:
            if isinstance(self.validators, (list, tuple,)):
                for validator in self.validators:
                    if callable(validator):
                        validator(value)
            elif callable(self.validators):
                self.validators(value)
        return value

    def empty(self, value):
        """ test if value is empty """
        return not value or value is None

    def _to_python(self, value):
        if value == None:
            return value
        return self.to_python(value)

    def _to_json(self, value):
        if value == None:
            return value
        return self.to_json(value)

    def to_python(self, value):
        """ convert to python type """
        return unicode(value)

    def to_json(self, value):
        """ convert to json, Converted value is saved in couchdb. """
        return self.to_python(value)

    data_type = None

class StringProperty(Property):
    """ string property str or unicode property 
    
    *Value type*: unicode
    """

    to_python = unicode

    def validate(self, value, required=True):
        value = super(StringProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if not isinstance(value, basestring):
            raise BadValueError(
                'Property %s must be unicode or str instance, not a %s' % (self.name, type(value).__name__))
        return value

    data_type = unicode

class IntegerProperty(Property):
    """ Integer property. map to int 
    
    *Value type*: int
    """
    to_python = int

    def empty(self, value):
        return value is None

    def validate(self, value, required=True):
        value = super(IntegerProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if value is not None and not isinstance(value, (int, long,)):
            raise BadValueError(
                'Property %s must be %s or long instance, not a %s'
                % (self.name, type(self.data_type).__name__,
                    type(value).__name__))

        return value

    data_type = int
LongProperty = IntegerProperty

class FloatProperty(Property):
    """ Float property, map to python float 
    
    *Value type*: float
    """
    to_python = float
    data_type = float

    def validate(self, value, required=True):
        value = super(FloatProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if not isinstance(value, float):
            raise BadValueError(
                'Property %s must be float instance, not a %s'
                % (self.name, type(value).__name__))

        return value
Number = FloatProperty

class BooleanProperty(Property):
    """ Boolean property, map to python bool
    
    *ValueType*: bool
    """
    to_python = bool
    data_type = bool

    def validate(self, value, required=True):
        value = super(BooleanProperty, self).validate(value,
                required=required)

        if value is None:
            return value

        if value is not None and not isinstance(value, bool):
            raise BadValueError(
                'Property %s must be bool instance, not a %s'
                % (self.name, type(value).__name__))

        return value

    def empty(self, value):
        """test if boolean is empty"""
        return value is None

class DecimalProperty(Property):
    """ Decimal property, map to Decimal python object
    
    *ValueType*: decimal.Decimal
    """
    data_type = decimal.Decimal

    def to_python(self, value):
        return decimal.Decimal(value)

    def to_json(self, value):
        return unicode(value)

class DateTimeProperty(Property):
    """DateTime property. It convert iso3339 string
    to python and vice-versa. Map to datetime.datetime
    object.
    
    *ValueType*: datetime.datetime
    """

    def __init__(self, verbose_name=None, auto_now=False, auto_now_add=False,
               **kwds):
        super(DateTimeProperty, self).__init__(verbose_name, **kwds)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def validate(self, value, required=True):
        value = super(DateTimeProperty, self).validate(value, required=required)

        if value is None:
            return value

        if value and not isinstance(value, self.data_type):
            raise BadValueError('Property %s must be a %s, current is %s' %
                          (self.name, self.data_type.__name__, type(value).__name__))
        return value

    def default_value(self):
        if self.auto_now or self.auto_now_add:
            return self.now()
        return Property.default_value(self)

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                value = value[0:19] # remove timezone
                value = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
            except ValueError, e:
                raise ValueError('Invalid ISO date/time %r [%s]' %
                        (value, str(e)))
        return value

    def to_json(self, value):
        if self.auto_now:
            value = self.now()

        if value is None:
            return value
        return value.replace(microsecond=0).isoformat() + 'Z'

    data_type = datetime.datetime

    @staticmethod
    def now():
        return datetime.datetime.utcnow()

class DateProperty(DateTimeProperty):
    """ Date property, like DateTime property but only
    for Date. Map to datetime.date object
    
    *ValueType*: datetime.date
    """
    data_type = datetime.date

    @staticmethod
    def now():
        return datetime.datetime.now().date()

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = datetime.date(*time.strptime(value, '%Y-%m-%d')[:3])
            except ValueError, e:
                raise ValueError('Invalid ISO date %r [%s]' % (value,
                    str(e)))
        return value

    def to_json(self, value):
        if value is None:
            return value
        return value.isoformat()

class TimeProperty(DateTimeProperty):
    """ Date property, like DateTime property but only
    for time. Map to datetime.time object
    
    *ValueType*: datetime.time
    """

    data_type = datetime.time

    @staticmethod
    def now(self):
        return datetime.datetime.now().time()

    def to_python(self, value):
        if isinstance(value, basestring):
            try:
                value = value.split('.', 1)[0] # strip out microseconds
                value = datetime.time(*time.strptime(value, '%H:%M:%S')[3:6])
            except ValueError, e:
                raise ValueError('Invalid ISO time %r [%s]' % (value,
                    str(e)))
        return value

    def to_json(self, value):
        if value is None:
            return value
        return value.replace(microsecond=0).isoformat()


class DictProperty(Property):
    """ A property that stores a dict of things"""

    def __init__(self, verbose_name=None, default=None,
        required=False, **kwds):
        """
        :args verbose_name: Optional verbose name.
        :args default: Optional default value; if omitted, an empty list is used.
        :args**kwds: Optional additional keyword arguments, passed to base class.

        Note that the only permissible value for 'required' is True.
        """

        if default is None:
            default = {}

        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)

    data_type = dict

    def validate(self, value, required=True):
        value = super(DictProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, dict):
                raise BadValueError('Property %s must be a dict' % self.name)
            value = self.validate_dict_contents(value)
        return value

    def validate_dict_contents(self, value):
        try:
            value = validate_dict_content(value)
        except BadValueError:
            raise BadValueError(
                'Items of %s dict must all be in %s' %
                    (self.name, ALLOWED_PROPERTY_TYPES))
        return value

    def default_value(self):
        """Default value for list.

        Because the property supplied to 'default' is a static value,
        that value must be shallow copied to prevent all fields with
        default values from sharing the same instance.

        Returns:
          Copy of the default value.
        """
        value = super(DictProperty, self).default_value()
        if value is None:
            value = {}
        return dict(value)

    def to_python(self, value):
        return LazyDict(value)

    def to_json(self, value):
        return value_to_json(value)



class ListProperty(Property):
    """A property that stores a list of things.

      """
    def __init__(self, verbose_name=None, default=None,
            required=False, item_type=None, **kwds):
        """Construct ListProperty.

    
         :args verbose_name: Optional verbose name.
         :args default: Optional default value; if omitted, an empty list is used.
         :args**kwds: Optional additional keyword arguments, passed to base class.

        
        """
        if default is None:
            default = []

        if item_type is not None and item_type not in ALLOWED_PROPERTY_TYPES:
            raise ValueError('item_type %s not in %s' % (item_type, ALLOWED_PROPERTY_TYPES))
        self.item_type = item_type

        Property.__init__(self, verbose_name, default=default,
            required=required, **kwds)

    data_type = list

    def validate(self, value, required=True):
        value = super(ListProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, list):
                raise BadValueError('Property %s must be a list' % self.name)
            value = self.validate_list_contents(value)
        return value

    def validate_list_contents(self, value):
        value = validate_list_content(value, item_type=self.item_type)
        try:
            value = validate_list_content(value, item_type=self.item_type)
        except BadValueError:
            raise BadValueError(
                'Items of %s list must all be in %s' %
                    (self.name, ALLOWED_PROPERTY_TYPES))
        return value

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
        return LazyList(value, item_type=self.item_type)

    def to_json(self, value):
        return value_to_json(value, item_type=self.item_type)


class StringListProperty(ListProperty):
    """ shorthand for list that should containe only unicode"""

    def __init__(self, verbose_name=None, default=None,
            required=False, **kwds):
        super(StringListProperty, self).__init__(verbose_name=verbose_name,
            default=default, required=required, item_type=basestring, **kwds)


class SetProperty(Property):
    """A property that stores a Python set as a list of unique
    elements.

    Note that Python set operations like union that return a set
    object do not alter list that will be stored with the next save,
    while operations like update that change a set object in-place do
    keep the list in sync.
    """
    def __init__(self, verbose_name=None, default=None, required=None,
                 item_type=None, **kwds):
        """Construct SetProperty.

         :args verbose_name: Optional verbose name.

         :args default: Optional default value; if omitted, an empty
                        set is used.

         :args required: True if field is required, default is False.

         :args item_type: Optional data type of items that set
                          contains.  Used to assist with JSON
                          serialization/deserialization when data is
                          stored/retireved.

         :args **kwds: Optional additional keyword arguments, passed to
                       base class.
         """
        if default is None:
            default = set()
        if item_type is not None and item_type not in ALLOWED_PROPERTY_TYPES:
            raise ValueError('item_type %s not in %s'
                             % (item_type, ALLOWED_PROPERTY_TYPES))
        self.item_type = item_type
        super(SetProperty, self).__init__(
            verbose_name=verbose_name, default=default, required=required,
            **kwds)

    data_type = set

    def validate(self, value, required=True):
        value = super(SetProperty, self).validate(value, required=required)
        if value and value is not None:
            if not isinstance(value, MutableSet):
                raise BadValueError('Property %s must be a set' % self.name)
            value = self.validate_set_contents(value)
        return value

    def validate_set_contents(self, value):
        try:
            value = validate_set_content(value, item_type=self.item_type)
        except BadValueError:
            raise BadValueError(
                'Items of %s set must all be in %s' %
                    (self.name, ALLOWED_PROPERTY_TYPES))
        return value

    def default_value(self):
        """Return default value for set.

        Because the property supplied to 'default' is a static value,
        that value must be shallow copied to prevent all fields with
        default values from sharing the same instance.

        Returns:
          Copy of the default value.
        """
        value = super(SetProperty, self).default_value()
        if value is None:
            return set()
        return value.copy()

    def to_python(self, value):
        return LazySet(value, item_type=self.item_type)

    def to_json(self, value):
        return value_to_json(value, item_type=self.item_type)


# structures proxy

class LazyDict(dict):
    """ object to make sure we keep updated of dict 
    in _doc. We just override a dict and maintain change in
    doc reference (doc[keyt] obviously).
    
    if init_vals is specified, doc is overwritten
    with the dict given. Otherwise, the values already in 
    doc are used. 
    """

    def __init__(self, doc, item_type=None, init_vals=None):
        dict.__init__(self)
        self.item_type = item_type

        self.doc = doc
        if init_vals is None:
            self._wrap()
        else:
            for key, value in init_vals.items():
                self[key] = value

    def _wrap(self):
        for key, json_value in self.doc.items():
            if isinstance(json_value, dict):
                value = LazyDict(json_value, item_type=self.item_type)
            elif isinstance(json_value, list):
                value = LazyList(json_value, item_type=self.item_type)
            else:
                value = value_to_python(json_value, self.item_type)
            dict.__setitem__(self, key, value)

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            self.doc[key] = {}
            value = LazyDict(self.doc[key], item_type=self.item_type, init_vals=value)
        elif isinstance(value, list):
            self.doc[key] = []
            value = LazyList(self.doc[key], item_type=self.item_type, init_vals=value)
        else:
            self.doc.update({key: value_to_json(value, item_type=self.item_type) })
        super(LazyDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        del self.doc[key]
        super(LazyDict, self).__delitem__(key)

    def pop(self, key, *args):
        default = len(args) == 1
        if default:
            self.doc.pop(key, args[-1])
            return super(LazyDict, self).pop(key, args[-1])
        self.doc.pop(key)
        return super(LazyDict, self).pop(key)

    def setdefault(self, key, default):
        if key in self:
            return self[key]
        self.doc.setdefault(key, value_to_json(default, item_type=self.item_type))
        super(LazyDict, self).setdefault(key, default)
        return default

    def update(self, value):
        for k, v in value.items():
            self[k] = v

    def popitem(self, value):
        new_value = super(LazyDict, self).popitem(value)
        self.doc.popitem(value_to_json(value, item_type=self.item_type))
        return new_value

    def clear(self):
        self.doc.clear()
        super(LazyDict, self).clear()

class LazyList(list):
    """ object to make sure we keep update of list 
    in _doc. We just override a list and maintain change in
    doc reference (doc[index] obviously).

    if init_vals is specified, doc is overwritten
    with the list given. Otherwise, the values already in 
    doc are used. 
    """

    def __init__(self, doc, item_type=None, init_vals=None):
        list.__init__(self)

        self.item_type = item_type
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
        for json_value in self.doc:
            if isinstance(json_value, dict):
                value = LazyDict(json_value, item_type=self.item_type)
            elif isinstance(json_value, list):
                value = LazyList(json_value, item_type=self.item_type)
            else:
                value = value_to_python(json_value, self.item_type)
            list.append(self, value)

    def __delitem__(self, index):
        del self.doc[index]
        list.__delitem__(self, index)

    def __setitem__(self, index, value):
        if isinstance(value, dict):
            self.doc[index] = {}
            value = LazyDict(self.doc[index], item_type=self.item_type, init_vals=value)
        elif isinstance(value, list):
            self.doc[index] = []
            value = LazyList(self.doc[index], item_type=self.item_type, init_vals=value)
        else:
            self.doc[index] = value_to_json(value, item_type=self.item_type)
        list.__setitem__(self, index, value)


    def __delslice__(self, i, j):
        del self.doc[i:j]
        list.__delslice__(self, i, j)

    def __getslice__(self, i, j):
        return LazyList(self.doc[i:j], self.item_type)

    def __setslice__(self, i, j, seq):
        self.doc[i:j] = (value_to_json(v, item_type=self.item_type) for v in seq)
        list.__setslice__(self, i, j, seq)

    def __contains__(self, value):
        jvalue = value_to_json(value)
        for m in self.doc:
            if m == jvalue: return True
        return False

    def append(self, *args, **kwargs):
        if args:
            assert len(args) == 1
            value = args[0]
        else:
            value = kwargs

        index = len(self)
        if isinstance(value, dict):
            self.doc.append({})
            value = LazyDict(self.doc[index], item_type=self.item_type, init_vals=value)
        elif isinstance(value, list):
            self.doc.append([])
            value = LazyList(self.doc[index], item_type=self.item_type, init_vals=value)
        else:
            self.doc.append(value_to_json(value, item_type=self.item_type))
        super(LazyList, self).append(value)

    def extend(self, x):
        self.doc.extend(
            [value_to_json(v, item_type=self.item_type) for v in x])
        super(LazyList, self).extend(x)

    def index(self, x, *args):
        x = value_to_json(x, item_type=self.item_type)
        return self.doc.index(x)

    def insert(self, i, x):
        self.__setslice__(i, i, [x])

    def pop(self, i=-1):
        del self.doc[i]
        v = super(LazyList, self).pop(i)
        return value_to_python(v, item_type=self.item_type)

    def remove(self, x):
        del self[self.index(x)]

    def sort(self, cmp=None, key=None, reverse=False):
        self.doc.sort(cmp, key, reverse)
        list.sort(self, cmp, key, reverse)

    def reverse(self):
        self.doc.reverse()
        list.reverse(self)


class LazySet(MutableSet):
    """Object to make sure that we keep set and _doc synchronized.

    We sub-class MutableSet and maintain changes in doc.

    Note that methods like union that return a set object do not
    alter _doc, while methods like update that change a set object
    in-place do keep _doc in sync.
    """
    def _map_named_operation(opname):
        fn = getattr(MutableSet, opname)
        if hasattr(fn, 'im_func'):
            fn = fn.im_func
        def method(self, other, fn=fn):
            if not isinstance(other, MutableSet):
                other = self._from_iterable(other)
            return fn(self, other)
        return method

    issubset = _map_named_operation('__le__')
    issuperset = _map_named_operation('__ge__')
    symmetric_difference = _map_named_operation('__xor__')

    def __init__(self, doc, item_type=None):
        self.item_type = item_type
        self.doc = doc
        self.elements = set(value_to_python(value, self.item_type)
                            for value in self.doc)

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, list(self))

    @classmethod
    def _from_iterable(cls, it):
        return cls(it)

    def __iand__(self, iterator):
        for value in (self.elements - iterator):
            self.elements.discard(value)
        return self

    def __iter__(self):
        return iter(element for element in self.elements)

    def __len__(self):
        return len(self.elements)

    def __contains__(self, item):
        return item in self.elements

    def __xor__(self, other):
        if not isinstance(other, MutableSet):
            if not is_iterable(Other):
                return NotImplemented
            other = self._from_iterable(other)
        return (self.elements - other) | (other - self.elements)

    def __gt__(self, other):
        if not isinstance(other, MutableSet):
            return NotImplemented
        return other < self.elements

    def __ge__(self, other):
        if not isinstance(other, MutableSet):
            return NotImplemented
        return other <= self.elements

    def __ne__(self, other):
        return not (self.elements == other)

    def add(self, value):
        self.elements.add(value)
        if value not in self.doc:
            self.doc.append(value_to_json(value, item_type=self.item_type))

    def copy(self):
        return self.elements.copy()

    def difference(self, other, *args):
        return self.elements.difference(other, *args)

    def difference_update(self, other, *args):
        for value in other:
            self.discard(value)
        for arg in args:
            self.difference_update(arg)

    def discard(self, value):
        self.elements.discard(value)
        try:
            self.doc.remove(value)
        except ValueError:
            pass

    def intersection(self, other, *args):
        return self.elements.intersection(other, *args)

    def intersection_update(self, other, *args):
        if not isinstance(other, MutableSet):
            other = set(other)
        for value in self.elements - other:
            self.discard(value)
        for arg in args:
            self.intersection_update(arg)

    def symmetric_difference_update(self, other):
        if not isinstance(other, MutableSet):
            other = set(other)
        for value in other:
            if value in self.elements:
                self.discard(value)
            else:
                self.add(value)

    def union(self, other, *args):
        return self.elements.union(other, *args)

    def update(self, other, *args):
        self.elements.update(other, *args)
        for element in self.elements:
            if element not in self.doc:
                self.doc.append(
                    value_to_json(element, item_type=self.item_type))

# some mapping

MAP_TYPES_PROPERTIES = {
        decimal.Decimal: DecimalProperty,
        datetime.datetime: DateTimeProperty,
        datetime.date: DateProperty,
        datetime.time: TimeProperty,
        str: StringProperty,
        unicode: StringProperty,
        bool: BooleanProperty,
        int: IntegerProperty,
        long: LongProperty,
        float: FloatProperty,
        list: ListProperty,
        dict: DictProperty,
        set: SetProperty,
}

def convert_property(value):
    """ convert a value to json from Property._to_json """
    if type(value) in MAP_TYPES_PROPERTIES:
        prop = MAP_TYPES_PROPERTIES[type(value)]()
        value = prop.to_json(value)
    return value


def value_to_property(value):
    """ Convert value in a Property object """
    if type(value) in MAP_TYPES_PROPERTIES:
        prop = MAP_TYPES_PROPERTIES[type(value)]()
        return prop
    else:
        return value

# utilities functions

def validate_list_content(value, item_type=None):
    """ validate type of values in a list """
    return [validate_content(item, item_type=item_type) for item in value]

def validate_dict_content(value, item_type=None):
    """ validate type of values in a dict """
    return dict([(k, validate_content(v,
                item_type=item_type)) for k, v in value.iteritems()])

def validate_set_content(value, item_type=None):
    """ validate type of values in a set """
    return set(validate_content(item, item_type=item_type) for item in value)

def validate_content(value, item_type=None):
    """ validate a value. test if value is in supported types """
    if isinstance(value, list):
        value = validate_list_content(value, item_type=item_type)
    elif isinstance(value, dict):
        value = validate_dict_content(value, item_type=item_type)
    elif item_type is not None and not isinstance(value, item_type):
        raise BadValueError(
            'Items  must all be in %s' % item_type)
    elif type(value) not in ALLOWED_PROPERTY_TYPES:
            raise BadValueError(
                'Items  must all be in %s' %
                    (ALLOWED_PROPERTY_TYPES))
    return value

def dict_to_json(value, item_type=None):
    """ convert a dict to json """
    return dict([(k, value_to_json(v, item_type=item_type)) for k, v in value.iteritems()])

def list_to_json(value, item_type=None):
    """ convert a list to json """
    return [value_to_json(item, item_type=item_type) for item in value]

def value_to_json(value, item_type=None):
    """ convert a value to json using appropriate regexp.
    For Dates we use ISO 8601. Decimal are converted to string.
    
    """
    if isinstance(value, datetime.datetime) and is_type_ok(item_type, datetime.datetime):
        value = value.replace(microsecond=0).isoformat() + 'Z'
    elif isinstance(value, datetime.date) and is_type_ok(item_type, datetime.date):
        value = value.isoformat()
    elif isinstance(value, datetime.time) and is_type_ok(item_type, datetime.time):
        value = value.replace(microsecond=0).isoformat()
    elif isinstance(value, decimal.Decimal) and is_type_ok(item_type, decimal.Decimal):
        value = unicode(value)
    elif isinstance(value, (list, MutableSet)):
        value = list_to_json(value, item_type)
    elif isinstance(value, dict):
        value = dict_to_json(value, item_type)
    return value

def is_type_ok(item_type, value_type):
    return item_type is None or item_type == value_type


def value_to_python(value, item_type=None):
    """ convert a json value to python type using regexp. values converted
    have been put in json via `value_to_json` .
    """
    data_type = None
    if isinstance(value, basestring):
        if re_date.match(value) and is_type_ok(item_type, datetime.date):
            data_type = datetime.date
        elif re_time.match(value) and is_type_ok(item_type, datetime.time):
            data_type = datetime.time
        elif re_datetime.match(value) and is_type_ok(item_type, datetime.datetime):
            data_type = datetime.datetime
        elif re_decimal.match(value) and is_type_ok(item_type, decimal.Decimal):
            data_type = decimal.Decimal
        if data_type is not None:
            prop = MAP_TYPES_PROPERTIES[data_type]()
            try:
                #sometimes regex fail so return value
                value = prop.to_python(value)
            except:
                pass
    elif isinstance(value, (list, MutableSet)):
        value = list_to_python(value, item_type=item_type)
    elif isinstance(value, dict):
        value = dict_to_python(value, item_type=item_type)
    return value

def list_to_python(value, item_type=None):
    """ convert a list of json values to python list """
    return [value_to_python(item, item_type=item_type) for item in value]

def dict_to_python(value, item_type=None):
    """ convert a json object values to python dict """
    return dict([(k, value_to_python(v, item_type=item_type)) for k, v in value.iteritems()])
