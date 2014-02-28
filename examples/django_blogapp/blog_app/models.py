from datetime import datetime

from couchdbkit.ext.django.schema import Document, StringProperty, \
    DateTimeProperty


class Post(Document):
    author = StringProperty()
    title = StringProperty()
    content = StringProperty()
    date = DateTimeProperty(default=datetime.utcnow)

class Comment(Document):
    author = StringProperty()
    content = StringProperty()
    date = DateTimeProperty(default=datetime.utcnow)
    post = StringProperty()
