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

This module providess a common interface for all CouchDB request. This
module makes HTTP request using :mod:`httplib2` module or :mod:`pycurl` 
if available. Just use set transport argument for this.

Example: 
    
    >>> resource = CouchdbResource()
    >>> info = resource.get()
    >>> info['couchdb']
    u'Welcome'

"""
import base64
import httplib
import restkit
from restkit.utils import url_quote
import re
import socket
import sys
import time
import types

import anyjson
        
from couchdbkit import __version__

USER_AGENT = 'couchdbkit/%s' % __version__

class ResourceNotFound(restkit.ResourceError):
    """ Exception raised when resource is not found"""

class ResourceConflict(restkit.ResourceError):
    """ Exception raised when there is conflict while updating"""

class PreconditionFailed(restkit.ResourceError):
    """ Exception raised when 412 HTTP error is received in response
    to a request """

RequestFailed = restkit.RequestFailed

class CouchDBResponse(restkit.httpc.HTTPResponse):
    
    @property
    def json_body(self):
        body = self.get_body()
        try:
            return anyjson.deserialize(body)
        except ValueError:
            return body


class CouchdbResource(restkit.Resource):

    def __init__(self, uri="http://127.0.0.1:5984", transport=None, 
            response_class=None, **client_opts):
        """Constructor for a `CouchdbResource` object.

        CouchdbResource represent an HTTP resource to CouchDB.

        @param uri: str, full uri to the server.
        @param transport: any http instance of object based on 
                `restkit.transport.HTTPTransportBase`. By 
                default it will use a client based on 
                `pycurl <http://pycurl.sourceforge.net/>`_ if 
                installed or `restkit.transport.HTTPLib2Transport`,
                a client based on `Httplib2 <http://code.google.com/p/httplib2/>`_ 
                or make your own depending on the options you need to access the 
                server (authentification, proxy, ....).
        @param use_proxy: boolean, default is False, if you want to use a proxy
        @param timeout: connection timeour, delay after a connection should be released
        @param min_size: minimum number of connections in the pool
        @param max_size: maximum number of connection in the pool
        @param pool_class: custom pool class
        """
        
        if response_class is None:
            response_class = CouchDBResponse
        
        restkit.Resource.__init__(self, uri=uri, transport=transport, 
                response_class=response_class, **client_opts)
        self.safe = ":/%"
        
    def copy(self, path=None, headers=None, **params):
        """ add copy to HTTP verbs """
        return self.request('COPY', path=path, headers=headers, **params)
        
    def request(self, method, path=None, payload=None, headers=None, **params):
        """ Perform HTTP call to the couchdb server and manage 
        JSON conversions, support GET, POST, PUT and DELETE.
        
        Usage example, get infos of a couchdb server on 
        http://127.0.0.1:5984 :


            import couchdbkit.CouchdbResource
            resource = couchdbkit.CouchdbResource()
            infos = resource.request('GET')

        @param method: str, the HTTP action to be performed: 
            'GET', 'HEAD', 'POST', 'PUT', or 'DELETE'
        @param path: str or list, path to add to the uri
        @param data: str or string or any object that could be
            converted to JSON.
        @param headers: dict, optional headers that will
            be added to HTTP request.
        @param raw: boolean, response return a Response object
        @param params: Optional parameterss added to the request. 
            Parameterss are for example the parameters for a view. See 
            `CouchDB View API reference 
            <http://wiki.apache.org/couchdb/HTTP_view_API>`_ for example.
        
        @return: tuple (data, resp), where resp is an `httplib2.Response` 
            object and data a python object (often a dict).
        """
        
        headers = headers or {}
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('User-Agent', USER_AGENT)

        body = None
        if payload is not None:
            #TODO: handle case we want to put in payload json file.
            if not hasattr(payload, 'read') and not isinstance(payload, basestring):
                body = anyjson.serialize(payload).encode('utf-8')
                headers.setdefault('Content-Type', 'application/json')
            else:
                body = payload

        params = encode_params(params)
        
        try:
            resp = restkit.Resource.request(self, method, path=path,
                             payload=body, headers=headers, **params)
                             
        except restkit.ResourceError, e:
            msg = getattr(e, 'msg', '')
            
            if e.response and msg:
                if e.response.headers.get('content-type') == 'application/json':
                    try:
                        msg = anyjson.deserialize(msg)
                    except ValueError:
                        pass
                    
            if type(msg) is dict:
                error = msg.get('reason')
            else:
                error = msg
                
            if e.status_int == 404:
                raise ResourceNotFound(error, http_code=404,
                        response=e.response)

            elif e.status_int == 409:
                raise ResourceConflict(error, http_code=409,
                        response=e.response)
            elif e.status_int == 412:
                raise PreconditionFailed(error, http_code=412,
                        response=e.response)
            else:
                raise 
        except:
            raise
        
        return resp

def encode_params(params):
    """ encode parameters in json if needed """
    _params = {}
    if params:
        for name, value in params.items():
            if name in ('key', 'startkey', 'endkey') \
                    or not isinstance(value, basestring):
                value = anyjson.serialize(value)
            _params[name] = value
    return _params

def escape_docid(docid):
    if docid.startswith('/'):
        docid = docid[1:]
    if docid.startswith('_design'):
        docid = '_design/%s' % url_quote(docid[8:], safe='')
    else:
        docid = url_quote(docid, safe='')
    return docid
    
re_sp = re.compile('\s')
def encode_attachments(attachments):
    for k, v in attachments.iteritems():
        if v.get('stub', False):
            continue
        else:
            v['data'] = re_sp.sub('', base64.b64encode(v['data']))
    return attachments