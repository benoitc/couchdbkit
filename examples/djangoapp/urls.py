from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'djangoapp.greeting.views.home'),
)

