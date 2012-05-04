# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license.
# See the NOTICE for more information.

from repoze.what.adapters import BaseSourceAdapter
from repoze.who.interfaces import IAuthenticator
from repoze.who.interfaces import IMetadataProvider
from zope.interface import implements

class GroupAdapter(BaseSourceAdapter):
    """ group adapter """

    def __init__(self, user_class):
        self.user_class = user_class

    def _get_all_sections(self):
        raise NotImplementedError()

    def _get_section_items(self, section):
        raise NotImplementedError()

    def _find_sections(self, hint):
        """Returns the group ids that the user is part of."""
        user = self.user_class.get(hint['repoze.what.userid'])
        return user.groups

    def _include_items(self, section, items):
        raise NotImplementedError()

    def _item_is_included(self, section, item):
        raise NotImplementedError()

    def _section_exists(self, section):
        raise NotImplementedError()

class PermissionAdapter(BaseSourceAdapter):
    def __init__(self, db):
        self.db = db

    def _get_all_sections(self):
        raise NotImplementedError()

    def _get_section_items(self, section):
        raise NotImplementedError()

    def _find_sections(self, hint):
        results = self.db.view('group/show_permissions', startkey=hint).all()
        return [x["value"] for x in results]

    def _include_items(self, section, items):
        raise NotImplementedError()

    def _item_is_included(self, section, item):
        raise NotImplementedError()

    def _section_exists(self, section):
        raise NotImplementedError()

class Authenticator(object):
    implements(IAuthenticator)

    def __init__(self, user_class):
        self.user_class = user_class

    def authenticate(self, environ, identity):
        login = identity.get('login', '')
        password = identity.get('password', '')

        user = self.user_class.authenticate(login, password)
        if not user:
            return None
        identity['login'] = str(user.login)
        identity['user'] = user
        return user._id

class MDPlugin(object):
    implements(IMetadataProvider)

    def __init__(self, user_class):
        self.user_class = user_class

    def add_metadata(self, environ, identity):
        if 'user' not in identity:
            uid = identity['repoze.who.userid']
            if uid:
                user = self.user_class.get(uid)
                identity['user'] = user
