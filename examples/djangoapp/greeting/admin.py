# -*- coding: utf-8 -*-

from django.contrib import admin
from couchdbkit.ext.django.admin import DocumentAdmin
from djangoapp.greeting.models import Greeting

class GreetingAdmin(DocumentAdmin):
    pass
admin.site.register(Greeting, DocumentAdmin)