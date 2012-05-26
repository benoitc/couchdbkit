from pyramid.config import Configurator
from pyramid.events import subscriber, NewRequest, ApplicationCreated
from couchdbkit import *

import logging
log = logging.getLogger(__name__)

@subscriber(NewRequest)
def add_couchdb_to_request(event):
    request = event.request
    settings = request.registry.settings
    db = settings['couchdb.server'].get_or_create_db(settings['couchdb.db'])
    event.request.db = db

@subscriber(ApplicationCreated)
def application_created_subscriber(event):
    settings = event.app.registry.settings
    db = settings['couchdb.server'].get_or_create_db(settings['couchdb.db'])

    try:
        """Test to see if our view exists.
        """
        db.view('lists/pages')
    except ResourceNotFound:
        design_doc = {
            '_id': '_design/lists',
            'language': 'javascript',
            'views': {
                'pages': {
                    'map': '''
                        function(doc) {
                            if (doc.doc_type === 'Page') {
                                emit([doc.page, doc._id], null)
                            }
                        }
                    '''
                }
            }
        }
        db.save_doc(design_doc)

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    """ Register server instance globally
    """
    config.registry.settings['couchdb.server'] = Server(uri=settings['couchdb.uri'])
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.scan()
    return config.make_wsgi_app()
