# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""
All exceptions used in couchdbkit.
"""

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
    def __init__(self, errors, *args):
        self.errors = errors

class ViewServerError(Exception):
    """ exception raised by view server"""
