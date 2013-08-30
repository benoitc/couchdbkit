from pyramid.config import Configurator
from pyramid.events import subscriber, ApplicationCreated
from couchdbkit import *

import logging
log = logging.getLogger(__name__)

@subscriber(ApplicationCreated)
def application_created_subscriber(event):
    registry = event.app.registry
    db = registry.db.get_or_create_db(registry.settings['couchdb.db'])

    pages_view_exists = db.doc_exist('lists/pages')
    if pages_view_exists == False:
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
    config.registry.db = Server(uri=settings['couchdb.uri'])

    def add_couchdb(request):
        db = config.registry.db.get_db(settings['couchdb.db'])
        return db

    config.add_request_method(add_couchdb, 'db', reify=True)

    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.scan()
    return config.make_wsgi_app()
