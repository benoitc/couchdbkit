# -*- coding: utf-8 -*-

from datetime import datetime
from django.shortcuts import render_to_response as render
from django.template import RequestContext, loader, Context

from couchdbkit.ext.django.loading import get_db

from djangoapp.greeting.models import Greeting

def home(request):
    db = get_db('greeting')
    greet = Greeting(
        author="Benoit",
        content="Welcome to simplecouchdb world",
        date=datetime.utcnow()
    )
   
    greet.save()
    
    return render("home.html", {
        "info": greet._db.info(),
        "id": greet.id
    }, context_instance=RequestContext(request))