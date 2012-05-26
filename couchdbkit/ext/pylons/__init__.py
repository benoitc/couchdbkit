# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""Pylons extension to simplify using couchdbkit with pylons. This features the
following:
 * Simple configuration
 * Authentication
 * View synchronization
 * Testing

Configuration
-------------
Add this to your ini file:

couchdb.uri = http://localhost:5984
couchdb.dbname = mydbname
cookies.secret = randomuniquestringforauth

And this into environment.py:

from couchdbkit.ext.pylons import init_from_config
init_from_config(config)

Authentication
--------------
You first need to define a User model, add this into model/user.py:

from couchdbkit import StringProperty
from couchdbkit.ext.pylons.auth.model import User as UserBase

class User(UserBase):
    first_name = StringProperty()
    last_name = StringProperty()
    email = StringProperty()

Then add this into middleware.py:
from yourapp.model.user import User
from couchdbkit.ext.pylons.auth.basic import AuthBasicMiddleware
app = AuthBasicMiddleware(app, config, User)

NOTE: This authentication by default uses sha-256 hashing with a salt, the behaviour
can be changed by overriding methods.

Now we need the views required for authentication:
Create yourapp/_design/user/views/by_login/map.js and make it look like this:
function(doc) {
    if(doc.doc_type == "User") {
        emit(doc.login, doc);
    }
}

And yourapp/_design/group/views/by_name/map.js:
function(doc) {
    if(doc.doc_type == "Group") {
        emit(doc.name, doc);
    }
}

And yourapp/_design/group/views/show_permissions/map.js:
function(doc) {
    if (doc.doc_type == "Group") {
        for (var i = 0; i < doc.permissions.length; i++) {
            emit(doc.name, doc.permissions[i].name);
        }
    }
}

View synchronization
--------------------
This will sync yourapp/_design to the CouchDB database described in the config.
couchdbkit has a built-in syncdb command that will automatically sync it. We
need to open up setup.py and add the command there as an entry point:

[paste.paster_command]
syncdb = couchdbkit.ext.pylons.commands:SyncDbCommand

And then add 'couchdbkit' to paster_plugins in the same file.

Syncing the database is then as simple as: paster syncdb /path/to/config.ini

Testing
-------
This will make it easier to create unit and functional tests that use couchdb
and load fixtures, this is not done yet and is TBC.

"""

from .db import init_from_config
