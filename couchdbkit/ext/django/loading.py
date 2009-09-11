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

"""
Maintain registry of documents used in your django project
and manage db sessions 
"""

import sys
import os

import urllib
import urlparse

from couchdbkit import Server, contain, ResourceConflict
from couchdbkit.loaders import FileSystemDocLoader
from couchdbkit.resource import PreconditionFailed
from django.conf import settings
from django.db.models import signals, get_app
from django.core.exceptions import ImproperlyConfigured
from django.utils.datastructures import SortedDict
from restkit.httpc import HttpClient, BasicAuth

COUCHDB_DATABASES = getattr(settings, "COUCHDB_DATABASES", [])

class CouchdbkitHandler(object):
    """ The couchdbkit handler for django """
    
    # share state between instances
    __shared_state__ = dict(
        _databases = {},
        app_schema = SortedDict()
    )    
       
    def __init__(self, databases, transport=None):
        """ initialize couchdbkit handler with COUCHDB_DATABASES
        settings """

        self.__dict__ = self.__shared_state__
        
        if transport is None:
            self.transport = HttpClient()
        # create databases sessions
        for app_name, uri in databases:
            if isinstance(uri, tuple):
                # case when you want to specify server uri 
                # and database name specifically. usefull
                # when you proxy couchdb on some path 
                server_part, dbname = uri
                parts = urlparse.urlsplit(urllib.unquote(server_part))
            else:
                parts = urlparse.urlsplit(urllib.unquote(uri))
                dbname = parts[2].split("/")[1]

            if parts[0] != 'http' and parts[0] != 'https':
                raise ValueError('Invalid dbstring')
            
            if "@" in parts[1]:
                server_parts = parts[1].split('@')
                if ":" in server_parts[0]:
                    username, password = server_parts[0].split(":")
                else:
                    username = server_parts[0]
                    password = ''
                server_uri = "%s://%s" % (parts[0], server_parts[1])
            else:
                server_uri = '%s://%s' % (parts[0], parts[1])
                username = password = ""
                     
            if username:
                self.transport.add_authorization(BasicAuth(username, password))
            server = Server(server_uri, self.transport)
            app_label = app_name.split('.')[-1]
            self._databases[app_label] = server[dbname]
    
    def sync(self, app, verbosity=2):
        """ used to sync views of all applications and eventually create
        database """
        app_name = app.__name__.rsplit('.', 1)[0]
        app_label = app_name.split('.')[-1]
        if app_label in self._databases:
            if verbosity >=1:
                print "sync `%s` in CouchDB" % app_name
            db = self._databases[app_label]
            try:
                db.server.create_db(db.dbname)
            except:
                pass
                
            app_path = os.path.abspath(os.path.join(sys.modules[app.__name__].__file__, ".."))
            loader = FileSystemDocLoader(app_path, "_design", design_name=app_label)
            loader.sync(db)
                
    def get_db(self, app_label):
        """ retrieve db session for a django application """
        return self._databases[app_label]
                
    def register_schema(self, app_label, *schema):
        """ register a Document object"""
        for s in schema:
            schema_name = schema[0].__name__.lower()
            schema_dict = self.app_schema.setdefault(app_label, SortedDict())
            if schema_name in schema_dict:
                fname1 = os.path.abspath(sys.modules[s.__module__].__file__)
                fname2 = os.path.abspath(sys.modules[schema_dict[schema_name].__module__].__file__)
                if os.path.splitext(fname1)[0] == os.path.splitext(fname2)[0]:
                    continue
            schema_dict[schema_name] = s
            s._db = self.get_db(app_label)

    def get_schema(self, app_label, schema_name):
        """ retriev Document object from its name and app name """
        return self.app_schema.get(app_label, SortedDict()).get(schema_name.lower())
        
couchdbkit_handler = CouchdbkitHandler(COUCHDB_DATABASES)
register_schema = couchdbkit_handler.register_schema
get_schema = couchdbkit_handler.get_schema
get_db = couchdbkit_handler.get_db
