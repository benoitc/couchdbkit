# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import os
from paste.deploy import loadapp
from paste.script.command import Command

from .db import sync_design, default_design_path

class SyncDbCommand(Command):
    """Syncs the CouchDB views on disk with the database.

    Example::

        $ paster syncdb my-development.ini

    This will also create the database if it does not exist
    """
    summary = __doc__.splitlines()[0]
    usage = '\n' + __doc__

    min_args = 1
    max_args = 1
    group_name = 'couchdbkit'
    default_verbosity = 3
    parser = Command.standard_parser(simulate=True)

    def command(self):
        """Main command to sync db"""
        config_file = self.args[0]

        config_name = 'config:%s' % config_file
        here_dir = os.getcwd()

        if not self.options.quiet:
            # Configure logging from the config file
            self.logging_file_config(config_file)

        # Load the wsgi app first so that everything is initialized right
        wsgiapp = loadapp(config_name, relative_to=here_dir)
        try:
            design_path = wsgiapp.config['couchdb.design']
        except KeyError:
            design_path = default_design_path(wsgiapp.config)

        # This syncs the main database.
        sync_design(wsgiapp.config['couchdb.db'], design_path)

