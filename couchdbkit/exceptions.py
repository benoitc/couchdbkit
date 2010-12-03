# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""
All exceptions used in couchdbkit.
"""
from restkit.errors import ResourceError

class InvalidAttachment(Exception):
    """ raised when an attachment is invalid """

class DuplicatePropertyError(Exception):
    """ exception raised when there is a duplicate 
    property in a model """

class BadValueError(Exception):
    """ exception raised when a value can't be validated 
    or is required """

class MultipleResultsFound(Exception):
    """ exception raised when more than one object is
    returned by the get_by method"""
    
class NoResultFound(Exception):
    """ exception returned when no results are found """
    
class ReservedWordError(Exception):
    """ exception raised when a reserved word
    is used in Document schema """
    
class DocsPathNotFound(Exception):
    """ exception raised when path given for docs isn't found """
    
class BulkSaveError(Exception):
    """ exception raised when bulk save contain errors.
    error are saved in `errors` property.
    """
    def __init__(self, errors, results, *args):
        self.errors = errors
        self.results = results

class ViewServerError(Exception):
    """ exception raised by view server"""

class MacroError(Exception):
    """ exception raised when macro parsiing error in functions """

class DesignerError(Exception):
    """ unkown exception raised by the designer """

class ResourceNotFound(ResourceError):
    """ Exception raised when resource is not found"""

class ResourceConflict(ResourceError):
    """ Exception raised when there is conflict while updating"""

class PreconditionFailed(ResourceError):
    """ Exception raised when 412 HTTP error is received in response
    to a request """
