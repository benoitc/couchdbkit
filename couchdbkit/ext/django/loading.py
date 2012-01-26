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

from restkit import BasicAuth
from couchdbkit import Server
from couchdbkit import push
from couchdbkit.resource import CouchdbResource
from couchdbkit.exceptions import ResourceNotFound
from django.conf import settings
from django.utils.datastructures import SortedDict

COUCHDB_DATABASES = getattr(settings, "COUCHDB_DATABASES", [])
COUCHDB_TIMEOUT = getattr(settings, "COUCHDB_TIMEOUT", 300)

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

        # Convert old style to new style
        if isinstance(databases, (list, tuple)):
            databases = dict(
                (app_name, {'URL': uri}) for app_name, uri in databases
            )

        # create databases sessions
        for app_name, app_setting in databases.iteritems():
            uri = app_setting['URL']

            # Blank credentials are valid for the admin party
            user = app_setting.get('USER', '')
            password = app_setting.get('PASSWORD', '')
            auth = BasicAuth(user, password)

            try:
                if isinstance(uri, (list, tuple)):
                    # case when you want to specify server uri
                    # and database name specifically. usefull
                    # when you proxy couchdb on some path
                    server_uri, dbname = uri
                else:
                    server_uri, dbname = uri.rsplit("/", 1)
            except ValueError:
                raise ValueError("couchdb uri [%s:%s] invalid" % (
                    app_name, uri))

            res = CouchdbResource(server_uri, timeout=COUCHDB_TIMEOUT, filters=[auth])

            server = Server(server_uri, resource_instance=res)
            app_label = app_name.split('.')[-1]
            self._databases[app_label] = (server, dbname)

    def sync(self, app, verbosity=2, temp=None):
        """ used to sync views of all applications and eventually create
        database.

        When temp is specified, it is appended to the app's name on the docid.
        It can then be updated in the background and copied over the existing
        design docs to reduce blocking time of view updates """
        app_name = app.__name__.rsplit('.', 1)[0]
        app_labels = set()
        schema_list = self.app_schema.values()
        for schema_dict in schema_list:
            for schema in schema_dict.values():
                app_module = schema.__module__.rsplit(".", 1)[0]
                if app_module == app_name and not schema._meta.app_label in app_labels:
                    app_labels.add(schema._meta.app_label)
        for app_label in app_labels:
            if not app_label in self._databases:
                continue
            if verbosity >=1:
                print "sync `%s` in CouchDB" % app_name
            db = self.get_db(app_label)

            app_path = os.path.abspath(os.path.join(sys.modules[app.__name__].__file__, ".."))
            design_path = "%s/%s" % (app_path, "_design")
            if not os.path.isdir(design_path):
                if settings.DEBUG:
                    print >>sys.stderr, "%s don't exists, no ddoc synchronized" % design_path
                return

            if temp:
                design_name = '%s-%s' % (app_label, temp)
            else:
                design_name = app_label

            docid = "_design/%s" % design_name

            push(os.path.join(app_path, "_design"), db, force=True,
                    docid=docid)

            if temp:
                ddoc = db[docid]
                view_names = ddoc.get('views', {}).keys()
                if len(view_names) > 0:
                    if verbosity >= 1:
                        print 'Triggering view rebuild'

                    view = '%s/%s' % (design_name, view_names[0])
                    list(db.view(view, limit=0))


    def copy_designs(self, app, temp, verbosity=2, delete=True):
        """ Copies temporary view over the existing ones

        This is used to reduce the waiting time for blocking view updates """

        app_name = app.__name__.rsplit('.', 1)[0]
        app_label = app_name.split('.')[-1]
        if app_label in self._databases:
            if verbosity >=1:
                print "Copy prepared design docs for `%s`" % app_name
            db = self.get_db(app_label)

            tmp_name = '%s-%s' % (app_label, temp)

            from_id = '_design/%s' % tmp_name
            to_id   = '_design/%s' % app_label

            try:
                db.copy_doc(from_id, to_id)

                if delete:
                    del db[from_id]

            except ResourceNotFound:
                print '%s not found.' % (from_id, )
                return


    def get_db(self, app_label, register=False):
        """ retrieve db session for a django application """
        if register:
            return

        db = self._databases[app_label]
        if isinstance(db, tuple):
            server, dbname = db
            db = server.get_or_create_db(dbname)
            self._databases[app_label] = db
        return db

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

    def get_schema(self, app_label, schema_name):
        """ retriev Document object from its name and app name """
        return self.app_schema.get(app_label, SortedDict()).get(schema_name.lower())

couchdbkit_handler = CouchdbkitHandler(COUCHDB_DATABASES)
register_schema = couchdbkit_handler.register_schema
get_schema = couchdbkit_handler.get_schema
get_db = couchdbkit_handler.get_db
