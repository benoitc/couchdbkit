# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
Extension to use couchdbkit in Django 1.x. It allows you to use couchdbkit
easily in your django projects.

Just add to your settings the `COUCHDB_DATABASES` that defines 

        COUCHDB_DATABASES = (
            ('djangoapp.greeting', 'http://127.0.0.1:5984/greeting'),
        )

This one define the db greeting on url `http://127.0.0.1:5984/greeting`
for the application `greeting`of djangoapp project.


Then add extension to your INSTALLED_APPS before all applications using
couchdbkit documents :

    INSTALLED_APPS = (
        ....
        'couchdbkit.ext.django',
        ....
    )

Add your documents objects in models.py : 

    from couchdbkit.ext.django.schema import *
    class Greeting(Document):
        author = StringProperty()
        content = StringProperty(required=True)
        date = DateTimeProperty(default=datetimee.utcnow)

and use it in your views.py :
        
    class GreetingForm(DocumentForm):
        
        class Meta:
            document = Greeting

    def home(request):
        
        greet = None
        
        if request.POST:
            form = GreetingForm(request.POST)
            if form.is_valid():
                greet = form.save()  
        else:
            form = GreetingForm()
            
        greetings = Greeting.view('greeting/all')
        
        return render("home.html", {
            "form": form,
            "greet": greet,
            "greetings": greetings
        }, context_instance=RequestContext(request)

You could notice in this example the `DocumentForm` object. 
This object works like the ModelForm object but for couchdb
documents. Very easy.

Views/shows/lists are created in _design folder of your application.
exemple :

    /yourapp
    /yourapp/_design
    /yourapp/_design/views
    /yourapp/_design/views/viewname
    /yourapp/_design/views/viewname/map.js
    ....

To create databases and sync views, just run the usual `syncdb` command.
It won't destroy your datas, just synchronize views.
"""

from django.db.models import signals

def syncdb(app, created_models, verbosity=2, **kwargs):
    """ function used by syncdb signal """
    from couchdbkit.ext.django.loading import couchdbkit_handler
    couchdbkit_handler.sync(app, verbosity=verbosity)

signals.post_syncdb.connect(syncdb)
