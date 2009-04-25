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
import re
import time

import couchdbkit.properties as p

__all__ = ['dict_to_json', 'list_to_json', 'value_to_json', 'MAP_TYPES_PROPERTIES',
'value_to_python', 'dict_to_python', 'list_to_python', 'convert_property']

MAP_TYPES_PROPERTIES = {
        decimal.Decimal: p.DecimalProperty,
        datetime.datetime: p.DateTimeProperty,
        datetime.date: p.DateProperty,
        datetime.time: p.TimeProperty,
        str: p.StringProperty,
        unicode: p.StringProperty,
        bool: p.BooleanProperty,
        int: p.IntegerProperty,
        long: p.LongProperty,
        float: p.FloatProperty
}

re_date = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$')
re_time = re.compile('^([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?$')
re_datetime = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])(\D?([01]\d|2[0-3])\D?([0-5]\d)\D?([0-5]\d)?\D?(\d{3})?([zZ]|([\+-])([01]\d|2[0-3])\D?([0-5]\d)?)?)?$')
re_decimal = re.compile('^(\d+).(\d+)$')

def convert_property(value):
    if type(value) in MAP_TYPES_PROPERTIES:
        prop = MAP_TYPES_PROPERTIES[type(value)]()
        value = prop.to_json(value)
    return value

def dict_to_json(value):
    ret = {}
    for k, v in value.iteritems():
        v = value_to_json(v)
        ret[k] = v
    return ret
    
def list_to_json(value):
    ret = []
    for item in value:
        item = value_to_json(item)
        ret.append(item)
    return ret
    
def value_to_json(value):
    if isinstance(value, datetime.datetime):
        value = value.replace(microsecond=0).isoformat() + 'Z'
    elif isinstance(value, datetime.date):
        value = o.isoformat()
    elif isinstance(value, datetime.time):
        value = value.replace(microsecond=0).isoformat()
    elif isinstance(value, decimal.Decimal):
        value = unicode(value) 
    elif isinstance(value, list):
        value = list_to_json(value)
    elif isinstance(value, dict):
        value = dict_to_json(value)
    return value
    
    
def value_to_python(value):
    data_type = None
    if isinstance(value, basestring):
        if re_date.match(value):
            data_type = datetime.date
        elif re_time.match(value):
            data_type = datetime.time
        elif re_datetime.match(value):
            data_type = datetime.datetime
        elif re_decimal.match(value):
            data_type = decimal.Decimal
        if data_type is not None:
            prop = MAP_TYPES_PROPERTIES[data_type]()
            value = prop.to_python(value)
                
    elif isinstance(value, list):
        value = list_to_python(value)
    elif isinstance(value, dict):
        value = dict_to_python(value)

    return value
    
def list_to_python(value):
    ret = []
    for item in value:
        item = value_to_python(item)   
        ret.append(item)       
    return ret
    
def dict_to_python(value):
    ret = {}
    for k, v in value.iteritems():
        v = value_to_python(v)
        ret[k] = v
    return ret