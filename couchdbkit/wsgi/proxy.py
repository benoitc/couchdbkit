# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.


from restkit.ext.wsgi_proxy import HostProxy, get_config

class CouchdbProxy(HostProxy):
    """A proxy to redirect all request to CouchDB database"""
    def __init__(self, db_name='', uri='http://127.0.0.1:5984',
            allowed_methods=['GET'], **kwargs):
        uri = uri.rstrip('/')
        if db_name:
            uri += '/' + db_name.strip('/')
        super(CouchdbProxy, self).__init__(uri, allowed_methods=allowed_methods,
                                        **kwargs)
                                        
def make_couchdb_proxy(global_config, db_name='', uri='http://127.0.0.1:5984',
            **local_config):
    """CouchdbProxy entry_point"""
    uri = uri.rstrip('/')
    config = get_config(local_config)
    print 'Running CouchdbProxy on %s/%s with %s' % (uri, db_name, config)
    return CouchdbProxy(db_name=db_name, uri=uri, **config)