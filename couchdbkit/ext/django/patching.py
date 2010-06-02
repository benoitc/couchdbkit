# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import sys

from django.db.models.base import ModelBase
from django.contrib.admin import ModelAdmin
import django.contrib.admin.sites

from couchdbkit.ext.django.admin import DocumentAdmin
from couchdbkit.ext.django.schema import DocumentMeta

def patch_admin():
    sites = sys.modules.pop('django.contrib.admin.sites')
    old_register = sites.AdminSite.register
    
    def register(self, model_or_iterable, admin_class=None, **options):
        if admin_class is not None and issubclass(admin_class, ModelAdmin):
            # no need to continue.
            return old_register(self, model_or_iterable, 
                admin_class=admin_class, **options)
        
        if isinstance(model_or_iterable, (ModelBase, DocumentMeta)):
            model_or_iterable = [model_or_iterable]
        
        if not admin_class or issubclass(admin_class, ModelAdmin):
            document_class = DocumentAdmin
        else:
            document_class = admin_class
            admin_class = None
            
        documents = []
        models = []
        for m in model_or_iterable:
            if isinstance(m, ModelBase):
                models.append(m)
            else:
                documents.append(m)
            
        for document in documents:
            if document in self._registry:
                raise AlreadyRegistered(
                'The document %s is already registered' % document.__name__)
                
            if options:
                options['__module__'] = __name__
                document_class = type("%sAdmin" % model.__name__, 
                    (document_class,), options)
            self._registry[document] = document_class(document, self)
        
        return old_register(self, models, admin_class=admin_class, 
                            **options)

    sites.AdminSite.register = register
    sys.modules['django.contrib.admin.sites'] = sites