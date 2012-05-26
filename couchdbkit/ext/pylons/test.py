# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement

import os
import unittest

from ... import BaseDocsLoader, ResourceNotFound
from .db import init_db, sync_design, default_design_path
from ...utils import json

class FixtureLoader(BaseDocsLoader):
    def __init__(self, directory):
        self._directory = directory

    def get_docs(self):
        docs = []
        for fixture in os.listdir(self._directory):
            fixture_path = os.path.join(self._directory, fixture)
            if not os.path.isfile(fixture_path):
                raise Exception("Fixture path %s not found" % fixture_path)
            with open(fixture_path, "r") as fp:
                for doc in json.load(fp):
                    docs.append(doc)
        return docs

class TestCase(unittest.TestCase):
    """
    Basic test class that will be default load all fixtures specified in the
    fixtures attribute.
    """
    def __init__(self, *args, **kwargs):
        self._config = kwargs['config']
        del kwargs['config']
        unittest.TestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        dbname = self._config['couchdb.db'].dbname

        # Set the directory to the fixtures.
        try:
            self._config['couchdb.db'].server.delete_db(dbname)
        except ResourceNotFound:
            pass

        self._config['couchdb.db'] = init_db(self._config['couchdb.uri'], dbname)
        sync_design(self._config['couchdb.db'], default_design_path(self._config))

        if hasattr(self, 'fixtures'):
            fixtures_dir = self._config['couchdb.fixtures']
            if not os.path.isdir(fixtures_dir):
                raise Exception("Fixtures dir %s not found" % fixtures_dir)
            FixtureLoader(fixtures_dir).sync(self._config['couchdb.db'])

