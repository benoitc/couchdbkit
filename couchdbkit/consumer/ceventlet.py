# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import select

from couchdbkit.consumer.async import AsyncConsumer 
from couchdbkit.utils import json

import eventlet
from eventlet.hubs import trampoline

class EventletConsumer(AsyncConsumer):
    def __init__(self, db, spawn=None):
        if spawn is None:
            spawn = eventlet.spawn_n
        eventlet.monkey_patch(socket=True, select=True)
        super(EventletConsumer, self).__init__(db, spawn=spawn)

    def sleep(self, t):
        eventlet.sleep(t)

    def wait_read(self, sock):
        res = select.select([sock.fileno()], [], [], 1.0)
        if res[0]:
            return True
        return False
