# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from hashlib import sha256
import os


from .... import Document, SchemaListProperty, StringProperty, \
StringListProperty

class Permission(Document):
    name = StringProperty(required=True)

class Group(Document):
    """
    Group class, contains multiple permissions.
    """
    name = StringProperty(required=True)
    permissions = SchemaListProperty(Permission)

class User(Document):
    """The base User model. This should be extended by the user."""
    login = StringProperty(required=True)
    password = StringProperty(required=True)
    groups = StringListProperty()

    @staticmethod
    def _hash_password(cleartext):
        if isinstance(cleartext, unicode):
            password_8bit = cleartext.encode('UTF-8')
        else:
            password_8bit = cleartext

        salt = sha256()
        salt.update(os.urandom(60))
        hash = sha256()
        hash.update(password_8bit + salt.hexdigest())
        hashed_password = salt.hexdigest() + hash.hexdigest()

        if not isinstance(hashed_password, unicode):
            hashed_password = hashed_password.decode('UTF-8')
        return hashed_password

    def set_password(self, password):
        self.password = self._hash_password(password)

    @staticmethod
    def authenticate(login, password):
        user = User.view("user/by_login", key=login).one()
        if not user:
            return None

        hashed_pass = sha256()
        hashed_pass.update(password + user.password[:64])
        if user.password[64:] != hashed_pass.hexdigest():
            return None
        return user

