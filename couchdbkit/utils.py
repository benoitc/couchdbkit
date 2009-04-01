#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2009 by Benoît Chesneau <benoitc@e-engura.com>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


__all__ = ['validate_dbname', 'SimplecouchdbJSONEncoder']

from calendar import timegm
import datetime
import decimal
import time
import re

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
