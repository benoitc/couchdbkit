# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import hashlib
import hmac

from django import http
from django.http import HttpResponse, Http404
from django.conf import settings
from django.core.servers.basehttp import is_hop_by_hop
import restkit

# max connections
DEFAULT_MAX_CONNECTIONS = 4
if hasattr(settings, "COUCHDBKIT_MAX_CONNECTIONS"):
    COUCHDBKIT_MAX_CONNECTIONS = getattr(settings, 
        "COUCHDBKIT_MAX_CONNECTIONS", DEFAULT_MAX_CONNECTIONS)
else:
    COUCHDBKIT_MAX_CONNECTIONS = DEFAULT_MAX_CONNECTIONS

# init the connections pool
pool = restkit.ConnectionPool(max_connections=COUCHDBKIT_MAX_CONNECTIONS)

# TODO: rewrite this aweful hack
def header_name(name):
    """Convert header name like HTTP_XXXX_XXX to Xxxx-Xxx
    """
    words = name[5:].split('_')
    for i in range(len(words)):
        words[i] = words[i][0].upper() + words[i][1:].lower()
        
    result = '-'.join(words)
    return result
    
def coerce_put_post(req):
    """
    Django doesn't particularly understand REST.
    In case we send data over PUT, Django won't
    actually look at the data and load it. We need
    to twist its arm here.
    
    The try/except abominiation here is due to a bug
    in mod_python. This should fix it.
    
    Function from django-piston project.
    """
    if req.method == "PUT":
        try:
            req.method = "POST"
            req._load_post_and_files()
            req.method = "PUT"
        except AttributeError:
            req.META['REQUEST_METHOD'] = 'POST'
            req._load_post_and_files()
            req.META['REQUEST_METHOD'] = 'PUT'
            
        req.PUT = req.POST    

def proxy(req, node_uri, prefix, path=None, headers=None):
    """ handle revproxy """
    headers = headers or {}
    
    host_uri = '%s://%s' % (req.is_secure() and 'https' or 'http',
                        req.get_host())
    
    
    for key, value in req.META.iteritems():
        if key.startswith('HTTP_'):
            key = header_name(key)
            
        elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            key = key.replace('_', '-')
            if not value: continue
        else:
            continue
        
        # rewrite location
        if key.lower() == "host":
            continue
        if is_hop_by_hop(key):
            continue
        else:
            headers[key] = value
            
    headers["X-Forwarded-For"] = req.META.get("REMOTE_ADDR")
    headers["X-Forwarded-Host"] = req.get_host()
    headers["PATH-INFO"] = req.get_full_path()
    if hasattr(req, 'user') and req.user.is_authenticated():
            headers.update({
                'X-Couchdbkit-User': req.user.username,
                'X-Couchdbkit-Groups': ','.join(str(g) \
                            for g in req.user.groups.all()),
                'X-Couchdbkit-Token': hmac.new(settings.SECRET_KEY, 
                            req.user.username, hashlib.sha1).hexdigest()
            })
                            
   
    # Django's internal mechanism doesn't pick up
    # PUT request, so we trick it a little here.
    if req.method.upper() == "PUT":
        coerce_put_post(req)
        
    req_uri = "%s/%s" % (node_uri, path or '')
    print req_uri
    try:
        resp = restkit.request(req_uri, method=req.method, 
                            body=req.raw_post_data,
                            headers=headers,
                            pool_instance=pool)
        body = resp.body_file
    except restkit.RequestFailed, e:
        msg = getattr(e, 'msg', '')
        
        if e.status_int >= 100:
            resp = e.response
            body = msg
        else:
            return http.HttpResponseBadRequest(msg)
             
    response = HttpResponse(body, status=resp.status_int)
    
    for k, v in resp.headers_list:
        if is_hop_by_hop(k):
            continue
        elif k == "location":
            if v.startswith(host_uri):
                v = v[len(host_uri):]
            print req.build_absolute_uri("%s%s" % (prefix, v))
            response[k] = req.build_absolute_uri("%s%s" % (prefix, v))
        else:
            response[k] = v
    return response

