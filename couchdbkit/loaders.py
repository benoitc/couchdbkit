# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""
Loaders are a simple way to manage design docs in your Python application. 
Loaders are compatible with couchapp script (http://github.com/couchapp/couchapp).
So it means that you can simply use couchdbkit as replacement for your python
applications with advantages of couchdbkit client. Compatibility with couchapp means that
you can also use macros to include javascript code or design doc members in your views,
shows & lists.

Loaders are FileSystemDocsLoader and FileSystemDocLoader. The first
one takes a directory and retrieve all design docs before sending them to
CouchDB. Second allow you to send only one design doc.

This module is here for compatibility reason and will be removed in 0.6.
It's replaced by couchdbkit.designer module and push* functions.
"""
from __future__ import with_statement

from .designer import document, push, pushapps, pushdocs

class BaseDocsLoader(object):
    """Baseclass for all doc loaders. """
   
    def get_docs(self):
        raise NotImplementedError

    def sync(self, dbs, atomic=True, **kwargs):
        raise NotImplementedError

class FileSystemDocsLoader(BaseDocsLoader):
    """ Load docs from the filesystem. This loader can find docs
    in folders on the filesystem and is the preferred way to load them. 
    
    The loader takes the path for design docs as a string  or if multiple
    locations are wanted a list of them which is then looked up in the
    given order:

    >>> loader = FileSystemDocsLoader('/path/to/templates')
    >>> loader = FileSystemDocsLoader(['/path/to/templates', '/other/path'])
    
    You could also do the same to loads docs.
    """

    def __init__(self, designpath, docpath=None):
        if isinstance(designpath, basestring):
            self.designpaths = [designpath]
        else:
            self.designpaths = designpath

        docpath = docpath or []
        if isinstance(docpath, basestring):
            docpath = [docpath]
        self.docpaths = docpath            
        

    def get_docs(self):
        docs = []
        for path in self.docpaths:
            ret = pushdocs(path, [], export=True)
            docs.extend(ret['docs'])

        for path in self.designpaths:
            ret = pushapps(path, [], export=True)
            docs.extend(ret['docs'])
        return docs

        
    def sync(self, dbs, atomic=True, **kwargs):
        for path in self.docpaths:
            pushdocs(path, dbs, atomic=atomic)

        for path in self.designpaths:
            pushapps(path, dbs, atomic=atomic)
 
class FileSystemDocLoader(BaseDocsLoader):
    """ Load only one design doc from a path on the filesystem.
        
        >>> loader = FileSystemDocLoader("/path/to/designdocfolder", "nameodesigndoc")
    """
    
    def __init__(self, designpath, name, design_name=None):
        self.designpath = designpath
        self.name = name
        if not design_name.startswith("_design"):
            design_name = "_design/%s" % design_name
        self.design_name = design_name

    def get_docs(self):
        return document(self.design_path, create=False,
                docid=self.design_name)

    def sync(self, dbs, atomic=True, **kwargs):
        push(self.design_path, dbs, atomic=atomic,
                docid=self.design_name)

