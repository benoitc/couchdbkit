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


class DocumentAdmin(object):
    __metaclass__ = forms.MediaDefiningClass
    
    
    def __init__(self, document, admin_site):
        self.document = document
        self.admin_site = admin_site

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)
            
            
        
