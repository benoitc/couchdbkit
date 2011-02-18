# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import os.path

from ...client import Server
from ...designer import pushapps
from ...schema import Document

def init_from_config(config):
    """Initialize the database given a pylons config. This assumes the
    configuration format layed out on the wiki. This will only initialize the
    primary database.

    This prefixes the database name with test_ if we're running unit tests.
    """
    uri = config['couchdb.uri']
    dbname = config['couchdb.dbname']

    config['couchdb.db'] = init_db(uri, dbname)
    config['couchdb.fixtures'] = os.path.join(config['pylons.paths']['root'], "fixtures")

def init_db(uri, dbname, main_db=True):
    """Returns a db object and syncs the design documents on demand.
    If main_db is set to true then all models will use that one by default.
    """
    server = Server(uri)

    db = server.get_or_create_db(dbname)
    if main_db:
        Document.set_db(db)
    return db

def sync_design(db, path):
    """Synchronizes the design documents with the database passed in."""
    pushapps(path, db)

def default_design_path(config):
    """Returns full path to the default design documents path, it's _design in
    the pylons root path
    """
    return os.path.join(config['pylons.paths']['root'], "_design")

