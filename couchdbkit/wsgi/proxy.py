# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import urlparse

from restkit.contrib.wsgi_proxy import HostProxy, get_config, ALLOWED_METHODS
from restkit.pool.simple import SimplePool
from webob import Request

class CouchdbProxy(object):
    """\
    WSGI application to proxy a couchdb server.
    
    Simple usage to proxy a CouchDB server on default url::
    
        from couchdbkit.wsgi import CouchdbProxy
        application = CouchdbProxy()
    """
    
    def __init__(self, uri="http://127.0.0.1:5984", pool=None,
            allowed_method=ALLOWED_METHODS, **local_config):
        if not pool:
            pool = SimplePool(keepalive=10)
        config = get_config(local_config)
        self.proxy = HostProxy(uri, pool=pool, 
                        allowed_methods=allowed_method, **config)
        
    def do_proxy(self, req, environ, start_response):
        """\
        return proxy response. Can be overrided to add authentification and 
        such. It's better to override do_proxy method than the __call__
        """
        return req.get_response(proxy)

    def __call__(self, environ, start_response):
        req = Request(environ)
        if 'RAW_URI' in req.environ:
            # gunicorn so we can use real path non encoded
            u = urlparse.urlparse(req.environ['RAW_URI'])
            req.environ['PATH_INFO'] = u.path
            
        resp = self.do_proy(req, environ, start_response)
        return resp(environ, start_response)
