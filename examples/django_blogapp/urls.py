from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^$', 'django_blogapp.blog_app.views.home'),
    url(r'^post/(?P<post_id>\w*)/$', 'django_blogapp.blog_app.views.view_post'),
    url(r'^post/edit/(?P<post_id>\w*)/$', 'django_blogapp.blog_app.views.edit_post'),
)
