# -*- coding: utf-8 -*-
# Copyright (C) 2007-2008 Christopher Lenz
# Copyright 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
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

class ViewResults(object):
    """
    Object to retrieve view results.
    """

    def __init__(self, view, **params):
        """
        Constructor of ViewResults object
        
        :attr view: Object inherited from :mod:`couchdbkit.client.view.ViewInterface
        :attr params: params to apply when fetching view.
        
        """
        self.view = view
        self.params = params
        self._result_cache = None
        self._total_rows = None
        self._offset = 0

    def iterator(self):
        self._fetch_if_needed()
        rows = self._result_cache.get('rows')
        if not rows:
            yield {}
        else:
            for row in rows:
                if self.view._wrapper is not None:
                    yield self.view._wrapper(row)
                else:
                    yield row
                    
    def one(self):
        return list(self)[0]

    def all(self):
        return list(self)

    def count(self):
        self._fetch_if_needed()
        return len(self._result_cache.get('rows', []))

    def fetch(self):
        self._result_cache = self.view._exec(**self.params)
        self._total_rows = self._result_cache.get('total_rows')
        self._offset = self._result_cache.get('offset', 0)

    def _fetch_if_needed(self):
        if not self._result_cache:
            self.fetch()

    @property
    def total_rows(self):
        if self._total_rows is None:
            return self.count()
        return self._total_rows

    @property
    def offset(self):
        self._fetch_if_needed() 
        return self._offset
        
    def __getitem__(self, key):
        params = self.params.copy()
        if type(key) is slice:
            if key.start is not None:
                params['startkey'] = key.start
            if key.stop is not None:
                params['endkey'] = key.stop
        elif isinstance(key, (list, tuple,)):
            params['keys'] = key
        else:
            params['key'] = key
        
        return ViewResults(self.view, params)
        
    def __iter__(self):
        return self.iterator()

    def __len__(self):
        return self.count()

    def __nonzero__(self):
        bool(len(self))
        
        
class ViewInterface(object):
    
    def __init__(self, db, wrapper=None):
        self._db = db
        self._wrapper = wrapper
        
    def __call__(self, **params):
        return ViewResults(self, **params)
        
    def _exec(self, **params):
        raise NotImplementedError
        
class View(ViewInterface):
    
    def __init__(self, db, view_path, wrapper=None):
        ViewInterface.__init__(self, db, wrapper=wrapper)
        self.view_path = view_path
        
    def _exec(self, **params):
        if 'keys' in params:
            return self._db.res.post(self.view_path, **params)
        else:
            return self._db.res.get(self.view_path, **params)
            

class TempView(ViewInterface):
    def __init__(self, db, design, wrapper=None):
        ViewInterface.__init__(self, db, wrapper=wrapper)
        self.design = design
        self._wrapper = wrapper

    def _exec(self, **params):
        return self._db.res.post('_temp_view', payload=self.design,
                **params)
