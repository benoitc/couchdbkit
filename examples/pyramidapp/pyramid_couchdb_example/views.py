import datetime

from pyramid.view import view_config

from couchdbkit import *

import logging
log = logging.getLogger(__name__)

class Page(Document):
    author = StringProperty()
    page = StringProperty()
    content = StringProperty()
    date = DateTimeProperty()

@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):

    def get_data():
        return list(request.db.view('lists/pages', startkey=['home'], \
                endkey=['home', {}], include_docs=True))

    page_data = get_data()

    if not page_data:
        Page.set_db(request.db)
        home = Page(
            author='Wendall',
            content='Using CouchDB via couchdbkit!',
            page='home',
            date=datetime.datetime.utcnow()
        )
        # save page data
        home.save()

        page_data = get_data()

    doc = page_data[0].get('doc')

    return {
        'project': 'pyramid_couchdb_example',
        'info': request.db.info(),
        'author': doc.get('author'),
        'content': doc.get('content'),
        'date': doc.get('date')
    }
