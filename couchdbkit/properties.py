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
import decimal
import datetime
import time

from couchdbkit.exceptions import *


__all__ = ['Property', 'StringProperty', 'IntegerProperty',
        'DecimalProperty', 'BooleanProperty', 'FloatProperty',
        'DateTimeProperty', 'DateProperty', 'TimeProperty']

class Property(object):
    """ Propertu base which all other properties
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
            value = self.to_python(value)
        
        return value

    def __set__(self, document_instance, value):
        value = self.validate(value, required=False)
        document_instance._doc[self.name] = self.to_json(value)

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
            if self.choices:
                match = False
                for choice in self.choices:
                    if choice == value:
                        match = True
                    if not match:
                        raise BadValueError('Property %s is %r; must be one of %r' % (
                            self.name, value, self.choices))
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

    def to_python(self, value):
        """ convert to python type """
        return unicode(value)

    def to_json(self, value):
        """ convert to json, These converetd value is saved in couchdb. """
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
                value = value.rstrip('Z') # remove timezone separator
                timestamp = timegm(time.strptime(value, '%Y-%m-%dT%H:%M:%S'))
                value = datetime.datetime.utcfromtimestamp(timestamp)
            except ValueError, e:
                raise ValueError('Invalid ISO date/time %r' % value)
        return value

    def to_json(self, value):
        if self.auto_now:
            value = self.now()
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
                raise ValueError('Invalid ISO date %r' % value)
        return value

    def to_json(self, value):
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
                raise ValueError('Invalid ISO time %r' % value)
        return value

    def to_json(self, value):
        return value.replace(microsecond=0).isoformat()