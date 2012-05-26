# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import logging
from paste.request import parse_dict_querystring, parse_formvars
from paste.httpexceptions import HTTPUnauthorized
from paste.httpheaders import CONTENT_LENGTH, CONTENT_TYPE
from repoze.what.middleware import setup_auth
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.who.interfaces import IChallenger, IIdentifier

import sys
from zope.interface import implements

from .adapters import GroupAdapter, PermissionAdapter, \
Authenticator, MDPlugin


class BasicAuth(object):
    """A basic challenger and identifier"""
    implements(IChallenger, IIdentifier)

    def __init__(self, login_url="/user/login", logout_url="/user/logout"):
        self._login_url = login_url
        self._logout_url = logout_url

    def identify(self, environ):
        path_info = environ['PATH_INFO']
        query = parse_dict_querystring(environ)

        # This will handle the logout request.
        if path_info == self._logout_url:
            # set in environ for self.challenge() to find later
            environ['repoze.who.application'] = HTTPUnauthorized()
            return None
        elif path_info == self._login_url:
            form = parse_formvars(environ)
            form.update(query)
            try:
                credentials = {
                    'login': form['login'],
                    'password': form['password']
                }
            except KeyError:
                credentials = None

            def auth_resp(environ, start_response):
                import json
                resp = {
                    "success": True
                }

                resp_str = json.dumps(resp)

                content_length = CONTENT_LENGTH.tuples(str(len(resp_str)))
                content_type = CONTENT_TYPE.tuples('application/json')
                headers = content_length + content_type
                start_response('200 OK', headers)
                return [resp_str]

            environ['repoze.who.application'] = auth_resp
            return credentials

    def challenge(self, environ, status, app_headers, forget_headers):
        cookies = [(h,v) for (h,v) in app_headers if h.lower() == 'set-cookie']
        if not forget_headers:
            return HTTPUnauthorized()

        def auth_form(environ, start_response):
            towrite = "Challenging this"
            content_length = CONTENT_LENGTH.tuples(str(len(towrite)))
            content_type = CONTENT_TYPE.tuples('text/html')
            headers = content_length + content_type + forget_headers
            start_response('200 OK', headers)
            return [towrite]
        return auth_form

    def remember(self, environ, identity):
        return environ['repoze.who.plugins']['cookie'].remember(environ, identity)

    def forget(self, environ, identity):
        return environ['repoze.who.plugins']['cookie'].forget(environ, identity)

def AuthBasicMiddleware(app, conf, user_class):
    groups = GroupAdapter(user_class)
    groups = {'all_groups': groups}
    permissions = {'all_perms': PermissionAdapter(conf["couchdb.db"])}

    basicauth = BasicAuth()
    cookie = AuthTktCookiePlugin(conf['cookies.secret'])

    who_args = {}
    who_args['authenticators'] = [('accounts', Authenticator(user_class))]
    who_args['challengers'] = [('basicauth', basicauth)]
    who_args['identifiers'] = [('basicauth', basicauth), ('cookie', cookie)]
    who_args['mdproviders'] = [('accounts', MDPlugin(user_class))]
    who_args['log_stream'] = sys.stdout
    who_args['log_level'] = logging.DEBUG

    return setup_auth(app, groups, permissions, **who_args)

