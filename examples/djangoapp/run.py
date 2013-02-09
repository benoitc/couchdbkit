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

from couchdbkit.wsgi.handler import WSGIHandler
import os
import sys

PROJECT_PATH = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(PROJECT_PATH)

os.environ['DJANGO_SETTINGS_MODULE'] = 'djangoapp.settings'

import django.core.handlers.wsgi
app = django.core.handlers.wsgi.WSGIHandler()

def main():
    handler = WSGIHandler(app)
    handler.run()
    
if __name__ == "__main__":
    main()
