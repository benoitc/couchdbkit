from datetime import datetime
from django.db import models

from couchdbkit.ext.django.schema import *

class Greeting(Document):
    author = StringProperty()
    content = StringProperty(required=True)
    date = DateTimeProperty(default=datetime.utcnow)
    
    class Meta:
        app_label = "greeting"
