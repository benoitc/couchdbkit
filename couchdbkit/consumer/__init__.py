# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.


from .base import ConsumerBase

OLD_CONSUMER_URIS = dict(
        eventlet = "couchdbkit.consumer.ceventlet.EventletConsumer",
        gevent = "couchdbkit.consumer.cgevent.GeventConsumer",
        sync = "couchdbkit.consumer.sync.SyncConsumer")

def load_consumer_class(uri):
    if uri in ('eventlet', 'gevent', 'sync'):
        import warnings
        warnings.warn(
                "Short names for uri in consumer backend are deprecated.",
                DeprecationWarning
                )
        uri = OLD_CONSUMER_URIS[uri] 

    components = uri.split('.')
    klass = components.pop(-1)
    mod = __import__('.'.join(components))
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return getattr(mod, klass)

class Consumer(object):
    """ Database change consumer
    
    Example Usage:
    
        >>> from couchdbkit import Server, Consumer
        >>> s = Server()
        >>> db = s['testdb']
        >>> c = Consumer(db)
        >>> def print_line(line):
        ...     print "got %s" % line
        ... 
        >>> c.wait(print_line,since=0) # Go into receive loop
         
    """

    def __init__(self, db, backend='couchdbkit.consumer.sync.SyncConsumer', **kwargs):
        """ Constructor for the consumer
        
        Args:
        @param db: Database instance
        @param backend: backend entry point uri
        The default class (sync) erialize each call to registered
        callbacks. Line processing should be fast in this case to not
        wait on socket read.

         A string referring to one of the following bundled classes:
        
        * ``sync``
        * ``eventlet`` - Requires eventlet >= 0.9.7
        * ``gevent``   - Requires gevent >= 0.12.2 (?)

        You can optionnaly register in ``couchdbkit.consumers``entry point 
        your own worker.
        """
        self.db = db
        self.consumer_class = load_consumer_class(backend)
        self._consumer = self.consumer_class(db, **kwargs)

    def fetch(self, cb=None, **params):
        """ Fetch all changes and return. If since is specified, fetch all changes
        since this doc sequence
        
        Args:
        @param params: kwargs
        See Changes API (http://wiki.apache.org/couchdb/HTTP_database_API#Changes)
        
        @return: dict, change result
        
        """
        return self._consumer.fetch(cb=cb, **params)

    def wait_once(self, cb=None, **params):
        """Wait for one change and return (longpoll feed) 
        
        Args:
        @param params: kwargs
        See Changes API (http://wiki.apache.org/couchdb/HTTP_database_API#Changes)
        
        @return: dict, change result
        """

        return self._consumer.wait_once(cb=cb, **params)

    def wait(self, cb, **params):
        """ Wait for changes until the connection close (continuous feed)
        
        Args:
        @param params: kwargs
        See Changes API (http://wiki.apache.org/couchdb/HTTP_database_API#Changes)
        
        @return: dict, line of change
        """
        return self._consumer.wait(cb, **params)

    def wait_once_async(self, cb, **params):
        """ like wait_once but doesn't return anything. """
        return self._consumer.wait_once_async(cb=cb, **params)

    def wait_async(self, cb, **params):
        """ like wait but doesn't return anything. """
        return self._consumer.wait_async(cb, **params)
