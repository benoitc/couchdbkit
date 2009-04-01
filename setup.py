#!/usr/bin/env python
# -*- coding: utf-8 -
#

try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages

import os
import sys

setup(
    name = 'couchdbkit',
    version = '0.1',

    description = 'Python couchdb kit',
    long_description = \
"""CouchDB is document oriented database. Couchdbkit framework try
to keep its simplicity when you manage it in python""",
    author = 'Benoit Chesneau',
    author_email = 'benoitc@e-engura.com',
    license = 'Apache License 2',
    url = 'http://code.google.com/p/py-simplecouchdb/',

    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Utilities',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages = find_packages(),
        
    zip_safe = False,

    install_requires = [
        'py-restclient>=1.2',
        'simplejson'
    ]

)
