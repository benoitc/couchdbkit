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
couchdb.resource
~~~~~~~~~~~~~~~~~~~~~~

This module provide a common interface for all CouchDB request. This
module make HTTP request using :mod:`httplib2` module or :mod:`pycurl` if available.

Example: 
    
    >>> resource = CouchdbResource()
    >>> info = resource.get()
    >>> info['couchdb']
    u'Welcome'

"""

import httplib
import restclient
from restclient.transport import HTTPResponse

import socket
import sys
import time
import types

# First we try to use simplejson if installed
# then json from python 2.6
try:
    import simplejson as json
except ImportError:
    import json
        
from couchdbkit import __version__
from couchdbkit.utils import SimplecouchdbJSONEncoder

USER_AGENT = 'couchdbkit/%s' % __version__

class ResourceConflict(restclient.ResourceError):
    """ Exception raised when there is conflict while updating"""

class PreconditionFailed(restclient.ResourceError):
    """ Exception raised when 412 HTTP error is received in response
    to a request """

ResourceNotFound = restclient.ResourceNotFound

class CouchdbResource(restclient.Resource):

    def __init__(self, uri="http://127.0.0.1:5984", transport=None):
        """Constructor for a `CouchdbResource` object.

        CouchdbResource represent an HTTP resource to CouchDB.

        :param uri: str, full uri to the server.
        :param transport: any http instance of object based on 
                `restclient.transport.HTTPTransportBase`. By 
                default it will use a client based on 
                `pycurl <http://pycurl.sourceforge.net/>`_ if 
                installed or `restclient.transport.HTTPLib2Transport`,
                a client based on `Httplib2 <http://code.google.com/p/httplib2/>`_ 
                or make yourown depending of the option you need to access to the 
                serve (authentification, proxy, ....).
        """
        
        restclient.Resource.__init__(self, uri=uri, transport=transport)
        self.client.safe = ":/"

    def copy(self, path=None, headers=None, **params):
        return self.request('COPY', path=path, headers=headers, **params)
        
    def request(self, method, path=None, payload=None, headers=None, **params):
        """ Perform HTTP call to the couchdb server and manage 
        JSON conversions, support GET, POST, PUT and DELETE.
        
        Usage example, get infos of a couchdb server on 
        http://127.0.0.1:5984 :

        .. code-block:: python

            import simplecouchdb.CouchdbResource
            resource = simplecouchdb.CouchdbResource()
            infos = resource.request('GET'))

        :param method: str, the HTTP action to be performed: 
            'GET', 'HEAD', 'POST', 'PUT', or 'DELETE'
        :param path: str or list, path to add to the uri
        :param data: str or string or any object that could be
            converted to JSON.
        :param headers: dict, optionnal headers that will
            be added to HTTP request.
        :param params: Optionnal parameterss added to the request. 
            Parameterss are for example the parameters for a view. See 
            `CouchDB View API reference 
            <http://wiki.apache.org/couchdb/HTTP_view_API>`_ for example.
        
        :return: tuple (data, resp), where resp is an `httplib2.Response` 
            object and data a python object (often a dict).
        """
        
        headers = headers or {}
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('User-Agent', USER_AGENT)

        # always init url safe chars
        self.client.safe=":/"

        body = None
        if payload is not None:
            if hasattr(payload, 'read'):
                # don't read the body now 
                # if content length is given
                if headers.get('Content-Length') is not None:
                    body = payload
                else:
                    body = payload.read()
            elif not isinstance(payload, basestring):
                body = json.dumps(payload, allow_nan=False,
                        ensure_ascii=False).encode('utf-8')
                headers.setdefault('Content-Type', 'application/json')
            else:
                body = payload

        if isinstance(body, basestring):
            headers.setdefault('Content-Length', str(len(body)))

        params = self.encode_params(params)

        def _make_request(retry=1):
            try:
                return restclient.Resource.request(self, method, path=path,
                        payload=body, headers=headers, **params)
            except (socket.error, httplib.BadStatusLine), e:
                if retry > 0:
                    time.sleep(0.4)
                    return _make_request(retry - 1)
                raise restclient.RequestFailed(e, http_code=0,
                        response=HTTPResponse({}))
            except restclient.RequestError, e: 
                # until py-restclient will be patched to only 
                # return RequestFailed, do our own raise
                raise restclient.RequestFailed(e, http_code=0,
                        response=HTTPResponse({}))
            except:
                raise
        try:
            data = _make_request()
        except restclient.RequestFailed, e:
            msg = getattr(e, 'msg', '')
            if msg and e.response.get('content-type') == 'application/json':
                
                try:
                    msg = json.loads(msg)
                except ValueError:
                    pass
                    
            if type(msg) is dict:
                error = msg.get('reason')
            else:
                error = msg

            if e.status_code == 409:
                raise ResourceConflict(error[1], http_code=409,
                        response=e.response)
            elif e.status_code == 412:
                raise PreconditionFailed(error, http_code=412,
                        response=e.response)
            else:
                raise 
        except:
            raise
        response = self.get_response()
        
        if data and response.get('content-type') == 'application/json':
            try:
                data = json.loads(data)
            except ValueError:
                pass
        
        return data

    def encode_params(self, params):
        _params = {}
        if params:
            for name, value in params.items():
                if name in ('key', 'startkey', 'endkey', 'keys') \
                        or not isinstance(value, basestring):
                    value = json.dumps(value, allow_nan=False,
                            ensure_ascii=False)
                _params[name] = value
        return _params
