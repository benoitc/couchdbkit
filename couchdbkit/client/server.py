# -*- coding: utf-8 -*-
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

from restclient.rest import url_quote

from couchdbkit.client.resource import CouchdbResource
from couchdbkit.client.database import Database
from couchdbkit.client.utils import validate_dbname

class Server(object):
    """ Server object that allow you to access and manage a couchdb node. 
    A Server object could be use like any `dict` object.
    """
    
    def __init__(self, uri='http://127.0.0.1:5984', transport=None):
        """
        Args: 
            uri: uri of CouchDb host
            transport: an transport instance from :mod:`restclient.transport`. Could be used
                to manage authentification to your server or proxy.
        """
        
        if not uri or uri is None:
            raise ValueError("Server uri is missing")

        self.uri = uri
        self.res = CouchdbResource(uri, transport=transport)
        
    def info(self):
        """ info of server 
        :return: dict
        """
        return self.res.get()
    
    def all_dbs(self):
        """ get list of databases in CouchDb host """
        result = self.res.get('/_all_dbs')
        return result
        
    def create_db(self, dbname):
        """ Create a database on CouchDb host

        :param dname: str, name of db

        :return: Database instance if it's ok or dict message
        """
        
        if "/" in dbname:
            dbname = url_quote(dbname, safe=":")
        res = self.res.put('/%s/' % validate_dbname(dbname))
        if res['ok']:
            return Database(self, dbname)
        return res['ok']
    
    def compact_db(self, dbname):
        if dbname in self:
            res = self.res.post('/%s/_compact' % dbname)
            return res['ok']
        return False
            
    def __getitem__(self, dbname):
        if dbname in self:
            return Database(self, dbname)
        raise KeyError("%s not in %s" % (dbname, self.uri))
        
    def __delitem__(self, dbname):
        return self.res.delete('/%s/' % validate_dbname(dbname))
        
    def __contains__(self, dbname):
        if dbname in self.all_dbs():
            return True
        return False
        
    def __iter__(self):
        for dbname in self.all_dbs():
            yield Database(self, dbname)

    def __len__(self):
        return len(self.all_dbs())
        
    def __nonzero__(self):
        return (len(self) > 0)
        

    