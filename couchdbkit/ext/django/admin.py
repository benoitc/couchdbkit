# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.contrib.admin.sites import AdminSite
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render_to_response as render
from django.template import RequestContext
from django.utils.functional import update_wrapper

from couchdbkit.ext.django.proxy import proxy

class CouchDBAdminSite(AdminSite):
    """ 
    Class to create custom admin site for couchdbkit.
    """
    DEFAULT_NODES = [('default', 'http://127.0.0.1:5984')]
    
    futons_index_template = None
    
    def get_urls(self):
        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)
            return update_wrapper(wrapper, view)
        
        urls = super(CouchDBAdminSite, self).get_urls()
        urls += patterns('',
            url(r'^couchdb/nodes/$', wrap(self.nodes), name="couchdb-nodes"),
            url(r'^couchdb/node/(?P<node_name>\w+)/(?P<node_path>.+)/$', 
                wrap(self.node)),
            url(r'^couchdb/node/(?P<node_name>\w+)/$', wrap(self.node))
        )
        return urls
        
    def get_nodes(self):
        if hasattr(settings, 'COUCHDB_NODES'):
            nodes = getattr(settings, 'COUCHDB_NODES', self.DEFAULT_NODES)
        else:
            nodes = self.DEFAULT_NODES
        return nodes
        
    def nodes(self, request):
        context = {
            'nodes': self.get_nodes()
        }
        return render(self.futons_index_template or 'couchdbkit/nodes.html', 
            context, context_instance=RequestContext(request))
            
    def node(self, request, node_name, node_path=None):
        path = request.get_full_path()
        if path.endswith("/"):
            path = path[:-1]

        ending = "/%s" % node_name
        if node_path:
            ending += "/%s" % node_path
        
        basepath = path.split(ending)[0]
        
        nodes = dict(self.get_nodes())
        node_uri = nodes.get(node_name)
        print node_name
        if not node_uri:
            raise Http404("%s not found" % node_name)
                             
        return proxy(request, node_uri, basepath, path=node_path)
            
        
site = CouchDBAdminSite()
        
        
