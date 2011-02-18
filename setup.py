# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import os
import sys

if not hasattr(sys, 'version_info') or sys.version_info < (2, 5, 0, 'final'):
    raise SystemExit("couchdbkit requires Python 2.5 or later.")

from setuptools import setup, find_packages
from couchdbkit import __version__

setup(
    name = 'couchdbkit',
    version = __version__,

    description = 'Python couchdb kit',
    long_description = file(
        os.path.join(
            os.path.dirname(__file__),
            'README.rst'
        )
    ).read(),
    author = 'Benoit Chesneau',
    author_email = 'benoitc@e-engura.com',
    license = 'Apache License 2',
    url = 'http://couchdbkit.org',

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
    packages = find_packages(exclude=['tests']),
        
    zip_safe = False,

    install_requires = [
        'restkit>=3.2',
    ],
    
    entry_points="""
    [couchdbkit.consumers]
    sync=couchdbkit.consumer.sync:SyncConsumer
    eventlet=couchdbkit.consumer.ceventlet:EventletConsumer
    gevent=couchdbkit.consumer.cgevent:GeventConsumer
    """,
        
    test_suite='noses',
)
