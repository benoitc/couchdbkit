from django.conf.urls.defaults import *
from django.contrib import admin

import couchdbkit.ext.django.admin as couchdbkit_admin

admin.autodiscover()


urlpatterns = patterns('',
    (r'^admin/', include(couchdbkit_admin.site.urls)),
    url(r'^$', 'djangoapp.greeting.views.home'),
    
)

