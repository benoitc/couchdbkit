# -*- coding: utf-8 -*-

from datetime import datetime
from django.shortcuts import render_to_response as render
from django.template import RequestContext, loader, Context

from couchdbkit.ext.django.forms import DocumentForm

from djangoapp.greeting.models import Greeting


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
        
    greetings = Greeting.view('greeting/all', descending=True)
    
    return render("home.html", {
        "form": form,
        "greet": greet,
        "greetings": greetings
    }, context_instance=RequestContext(request))