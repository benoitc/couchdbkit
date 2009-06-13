from django.db import models

from couchdbkit.ext.django.schema import *

class Greeting(Document):
    author = StringProperty()
    content = StringProperty()
    date = DateTimeProperty()