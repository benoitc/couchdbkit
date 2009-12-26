#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008,2009 Benoit Chesneau <benoitc@e-engura.org>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at#
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import couchdbkit
from couchdbkit.contrib import WSGIHandler
import json

def app(environ, start_response):
    """Simplest possible application object"""
    data = 'Hello, World!\n DB Infos : %s\n'  % json.dumps(environ["COUCHDB_INFO"])
    status = '200 OK'
    response_headers = [
        ('Content-type','text/plain'),
        ('Content-Length', len(data))
    ]
    start_response(status, response_headers)
    return [data]
    
def main():
    handler = WSGIHandler(app)
    handler.run()
    
if __name__ == "__main__":
    main()
