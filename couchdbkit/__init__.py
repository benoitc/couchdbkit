# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

version_info = (0, 4, 6)
__version__ =  ".".join(map(str, version_info))

try:
    from couchdbkit.resource import ResourceNotFound, ResourceConflict,\
RequestFailed, PreconditionFailed, CouchdbResource

    from couchdbkit.exceptions import InvalidAttachment, DuplicatePropertyError,\
BadValueError, MultipleResultsFound, NoResultFound, ReservedWordError,\
DocsPathNotFound, BulkSaveError

    from couchdbkit.client import Server, Database, ViewResults, View, TempView
    from couchdbkit.consumer import Consumer
    from couchdbkit.external import External
    from couchdbkit.loaders import BaseDocsLoader, FileSystemDocsLoader
    
    from couchdbkit.schema import Property, Property, IntegerProperty,\
DecimalProperty, BooleanProperty, FloatProperty, DateTimeProperty,\
DateProperty, TimeProperty, dict_to_json, dict_to_json, dict_to_json,\
value_to_python, dict_to_python, DocumentSchema, DocumentBase, Document,\
StaticDocument, QueryMixin, AttachmentMixin, SchemaProperty, SchemaListProperty,\
ListProperty, DictProperty, StringListProperty, contain, StringProperty

except ImportError:
    import traceback
    traceback.print_exc()