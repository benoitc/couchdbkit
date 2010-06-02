# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from django import forms
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
            
        info = self.opts.app_label, self.opts.module_name
        
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
        
    def urls(self):
        return self.get_urls()
    urls = property(urls)
    
    def has_add_permission(self, request):
        "Returns True if the given request has permission to add an object."
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_add_permission())

    def has_change_permission(self, request, obj=None):
        """
        Returns True if the given request has permission to change the given
        Django model instance.

        If `obj` is None, this should return True if the given request has
        permission to change *any* object of the given type.
        """
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_change_permission())

    def has_delete_permission(self, request, obj=None):
        """
        Returns True if the given request has permission to change the given
        Django model instance.

        If `obj` is None, this should return True if the given request has
        permission to delete *any* object of the given type.
        """
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_delete_permission())

    def get_model_perms(self, request):
        """
        Returns a dict of all perms for this model. This dict has the keys
        ``add``, ``change``, and ``delete`` mapping to the True/False for each
        of those actions.
        """
        return {
            'add': self.has_add_permission(request),
            'change': self.has_change_permission(request),
            'delete': self.has_delete_permission(request),
        }
            
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