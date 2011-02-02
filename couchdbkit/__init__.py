# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

version_info = (0, 5, 2)
__version__ =  ".".join(map(str, version_info))

try:
    from couchdbkit.resource import RequestFailed,CouchdbResource

    from couchdbkit.exceptions import InvalidAttachment, DuplicatePropertyError,\
BadValueError, MultipleResultsFound, NoResultFound, ReservedWordError,\
DocsPathNotFound, BulkSaveError, ResourceNotFound, ResourceConflict, \
PreconditionFailed

    from couchdbkit.client import Server, Database, ViewResults, View, TempView
    from couchdbkit.consumer import Consumer
    from couchdbkit.designer import document, push, pushdocs, pushapps, clone
    from couchdbkit.external import External
    from couchdbkit.loaders import BaseDocsLoader, FileSystemDocsLoader
    
    from couchdbkit.schema import Property, Property, IntegerProperty,\
DecimalProperty, BooleanProperty, FloatProperty, DateTimeProperty,\
DateProperty, TimeProperty, dict_to_json, dict_to_json, dict_to_json,\
value_to_python, dict_to_python, DocumentSchema, DocumentBase, Document,\
StaticDocument, QueryMixin, AttachmentMixin, SchemaProperty, SchemaListProperty,\
SchemaDictProperty, \
ListProperty, DictProperty, StringListProperty, contain, StringProperty

except ImportError:
    import traceback
    traceback.print_exc()

import logging    

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG
}

def set_logging(level, handler=None):
    """
    Set level of logging, and choose where to display/save logs 
    (file or standard output).
    """
    if not handler:
        handler = logging.StreamHandler()

    loglevel = LOG_LEVELS.get(level, logging.INFO)
    logger = logging.getLogger('couchdbkit')
    logger.setLevel(loglevel)
    format = r"%(asctime)s [%(process)d] [%(levelname)s] %(message)s"
    datefmt = r"%Y-%m-%d %H:%M:%S"
    
    handler.setFormatter(logging.Formatter(format, datefmt))
    logger.addHandler(handler)

