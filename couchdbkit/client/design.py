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


import uuid

from couchdbkit.resource import ResourceConflict
from couchdbkit.client import document

__all__ = ['Design']

class Design(document.Document):
    """ design is a Design document object. 
    It allow you to create an save a  document it is inherited
    from :class::`simplecouchdb.core.document.Document`

    simple usage :

    .. code-block:: python
        
        from simplecouchdb.core.design import Design
        d = Design()
        myview = d.view_by('key1', 'key2')
        for row in view_results:
            ....
    """

    def view(self, view_name, wrapper=None, **params):
        if self._db is None:
            raise TypeError("database required to fetch view")
        
        view_path = "%s/%s" % (self.name, view_name)
        return self._db.view(view_path, wrapper=wrapper, **params)

    def get_name(self):
        if not '_id' in self:
            return None
        return self['_id'].replace('_design/', '')

    def set_name(self, name):
        if name.startswith('/'):
            name = name[1:]
        if not name.startswith('_design/'):
            name = "_design/%s" % name
        if not self.new_document and name != self.id:
            del self['_rev']
        self['_id'] = name
    
    name = property(get_name, set_name)

    def has_view(self, view):
        if 'views' in self:
            return self['views'].get(view)
        return None

    def save(self, force_update=False):
        if self._db is None:
            raise TypeError("doc database required to save document")

        if not '_id' in self:
            raise TypeError("name is required before save it.")
                    
        try:
            self._db.save(self)
        except ResourceConflict:
            current = self._db.get(self.id)
            if force_update or not 'views' in current:
                self['_rev'] = current['_rev']
                self._db.save(self)
            else:
                should_save = False
                for method_name, view in self['views'].iteritems():
                    if current['views'].get('method_name') != view:
                        should_save = True
                        break
                if should_save:
                    self['_rev'] = current['_rev']
                    self._db.save(self)

