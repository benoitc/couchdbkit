# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

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
from couchdbkit.resource import CouchdbResource, PreconditionFailed
from django.conf import settings
from django.db.models import signals, get_app
from django.core.exceptions import ImproperlyConfigured
from django.utils.datastructures import SortedDict
from restkit import BasicAuth

COUCHDB_DATABASES = getattr(settings, "COUCHDB_DATABASES", [])
COUCHDB_TIMEOUT = getattr(settings, "COUCHDB_TIMEOUT", 300)


class DjangoappDocLoader(FileSystemDocLoader):
    """ Class overriding FileSystemDocLoaders to 
    add couchdbkit admin views.
    """
    
    COUCHDBKIT_VIEWS = {
        "couchdbkit_doctypes": {
            "map": """
function(doc) {
    if (doc.doc_type) {
        emit(doc.doc_type, null);
    }
}"""
        }
    }
    
    def get_docs(self, verbose=False):
        docs = super(DjangoappDocLoader, self).get_docs(verbose=verbose)
        for doc in docs:
            doc["views"].update(self.COUCHDBKIT_VIEWS)
        return docs
    
    

class CouchdbkitHandler(object):
    """ The couchdbkit handler for django """

    # share state between instances
    __shared_state__ = dict(
            _databases = {},
            app_schema = SortedDict()
            )    

    def __init__(self, databases):
        """ initialize couchdbkit handler with COUCHDB_DATABASES
        settings """

        self.__dict__ = self.__shared_state__

        # create databases sessions
        for app_name, uri in databases:

            try:
                if isinstance(uri, tuple):
                    # case when you want to specify server uri 
                    # and database name specifically. usefull
                    # when you proxy couchdb on some path 
                    server_uri, dbname = uri
                else:
                    server_uri, dbname = uri.rsplit("/", 1)
            except ValueError:
                raise ValueError("couchdb uri [%s:%s] invalid" % (
                    app_name, uri))

            res = CouchdbResource(server_uri, timeout=COUCHDB_TIMEOUT)

            server = Server(server_uri, resource_instance=res)
            app_label = app_name.split('.')[-1]
            self._databases[app_label] = server.get_or_create_db(dbname)
    
    def sync(self, app, verbosity=2):
        """ used to sync views of all applications and eventually create
        database.
        """
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
            design_path = "%s/%s" % (app_path, "_design")
            if not os.path.isdir(design_path):
                if settings.DEBUG:
                    print >>sys.stderr, "%s don't exists, no ddoc synchronized" % design_path
                return
            loader = DjangoappDocLoader(app_path, "_design", design_name=app_label)
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
