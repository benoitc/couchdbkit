#!/usr/bin/env python
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


import codecs
import string
from calendar import timegm
import datetime
import decimal
from hashlib import md5
import os
import re
import sys
import time


# python 2.6
try: 
    import simplejson
except ImportError:
    import json

VALID_DB_NAME = re.compile(r'^[a-z0-9_$()+-/]+$')
def validate_dbname(name):
    """ validate dbname """
    if not VALID_DB_NAME.match(name):
        raise ValueError('Invalid database name')
    return name
    
def to_bytestring(s):
    """ convert to bytestring an unicode """
    if not isinstance(s, basestring):
        return s
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return s
    
def read_file(fname):
    """ read file content"""
    f = codecs.open(fname, 'rb', "utf-8")
    data = f.read()
    f.close()
    return data

def sign_file(file_path):
    """ return md5 hash from file content
    
    :attr file_path: string, path of file
    
    :return: string, md5 hexdigest
    """
    if os.path.isfile(file_path):
        f = open(file_path, 'rb')
        content = f.read()
        f.close()
        return md5(content).hexdigest()
    return ''

def write_content(fname, content):
    """ write content in a file
    
    :attr fname: string,filename
    :attr content: string
    """
    f = open(fname, 'wb')
    f.write(to_bytestring(content))
    f.close()

def write_json(filename, content):
    """ serialize content in json and save it
    
    :attr filename: string
    :attr content: string
    
    """
    write_content(filename, json.dumps(content))

def read_json(filename, use_environment=False):
    """ read a json file and deserialize
    
    :attr filename: string
    :attr use_environment: boolean, default is False. If
    True, replace environment variable by their value in file
    content
    
    :return: dict or list
    """
    try:
        data = read_file(filename)
    except IOError, e:
        if e[0] == 2:
            return {}
        raise

    if use_environment:
        data = string.Template(data).substitute(os.environ)

    try:
        data = json.loads(data)
    except ValueError:
        print >>sys.stderr, "Json is invalid, can't load %s" % filename
        raise
    return data

class SimplecouchdbJSONEncoder(simplejson.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time and decimal types. 
    """
    
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return  o.replace(microsecond=0).isoformat() + 'Z'
        
        if isinstance(o, datetime.date):
            return o.isoformat()
        
        if isinstance(o, datetime.time):
            
            return o.replace(microsecond=0).isoformat()
        
        if isinstance(o, decimal.Decimal):
            return  unicode(o)
        
        return super(SimplecouchdbJSONEncoder, self).default(o)
