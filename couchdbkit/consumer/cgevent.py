# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.



from couchdbkit.consumer.async import AsyncConsumer 
from couchdbkit.utils import json

import gevent
from gevent import socket
from gevent import select

class GeventConsumer(AsyncConsumer):
    def __init__(self, db, spawn=None):
        if spawn is None:
            spawn = gevent.spawn

        super(GeventConsumer, self).__init__(db, spawn=spawn)

    def sleep(self, t):
        gevent.sleep(t)

    def wait_read(self, sock):
        res = select.select([sock.fileno()], [], [], 1.0)
        if res[0]:
            return True
        return False

    def patch_socket(self, sock):
        sock = socket.socket(_sock=sock)
        return sock
