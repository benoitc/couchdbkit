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
        self.opts = document._meta

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)
            
        info = self.model._meta.app_label, self.model._meta.module_name
        
        urlpatterns = patterns('',
            url(r'^$',
                wrap(self.changelist_view),
                name='%s_%s_changelist' % info),
            url(r'^add/$',
                wrap(self.add_view),
                name='%s_%s_add' % info),
            url(r'^(.+)/history/$',
                wrap(self.history_view),
                name='%s_%s_history' % info),
            url(r'^(.+)/delete/$',
                wrap(self.delete_view),
                name='%s_%s_delete' % info),
            url(r'^(.+)/$',
                wrap(self.change_view),
                name='%s_%s_change' % info),
        )
        return urlpatterns
            
    def changelist_view(self, request, extra_context=None):
        raise NotImplementedError
        
    def add_view(self, request, extra_context=None):
        raise NotImplementedError
        
    def history_view(self, request, extra_context=None):
        raise NotImplementedError

    def delete_view(self, request, extra_context=None):
        raise NotImplementedError

    def change_view(self, request, extra_context=None):
        raise NotImplementedError