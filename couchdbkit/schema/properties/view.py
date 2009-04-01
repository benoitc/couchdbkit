# -*- coding: utf-8 -*-
# Copyright 2009 by Benoît Chesneau <benoitc@e-engura.org>
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
#

from couchdbkit.schema.properties import Property
from couchdbkit.design import ViewDef

class ViewProperty(object):
    
    def __init__(self, name, verbose_name=None, 
            fun_map=None, fun_reduce=None, language='javascript'):
        
        self.name = name    
        self.verbose_name = verbose_name
        self.fun_map = fun_map
        self.fun_reduce = fun_reducce
        self.language = language
        
        self._view_def = ViewDef(name, fun_map=fun_map,
                fun_reduce=fun_reduce, language=language)
          
    def __get__(self, document_instance, document_class):
        def _wrapper(row):
            if not isinstance(row, dict) or not 'id' in row:
                return row
            data = row['value']
            data['_id'] = row.get('id')
            obj = document_class.wrap(data)
            return obj
        
        if document_instance is None:
            return self
            
        if not document_class._db or document_class._db is None:
            raise ValueError("db is not  set in %s"  % self.document_class.__name__ )
            
        return self._view_def(document_class._db, wrapper=_wrapper)