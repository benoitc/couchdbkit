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

Current loaders are FileSystemDocsLoader and FileSystemDocLoader. The first
one takes a directory and retrieve all design docs before sending them to
CouchDB. Second allow you to send only one design doc.
"""
from __future__ import with_statement

import base64
import copy
import httplib
import mimetypes
import os
import socket
import sys

import anyjson

from couchdbkit.exceptions import DocsPathNotFound
from couchdbkit.resource import ResourceNotFound
from couchdbkit.utils import *
from couchdbkit.macros import *

class BaseDocsLoader(object):
    """Baseclass for all doc loaders.  Subclass this and override `get_docs` to
    implement a custom loading mechanism.  You can then sync docs and design docs
    to the db with the `sync` function.

    A very basic example for a loader that looks up a json file on the
    filesystem could look like this::

        from couchdbkit import BaseDocsLoader
        import os
        import anyjson

        class MyDocsLoader(BaseDocsLoader):

            def __init__(self, path):
                self.path = path

            def get_docs(self,):
                if not os.path.exists(path):
                    raise DocsPathNotFound
                with file(path) as f:
                    source = anyjson.deserialize(f.read().decode('utf-8'))
                return source
    """
    
    def get_docs(self):
        raise NotImplementedError
    
    def sync(self, dbs, atomic=True, verbose=False):
        if not isinstance(dbs, (list, tuple)):
            dbs = [dbs]
        
        doc_or_docs = self.get_docs()
        if not isinstance(doc_or_docs, (list, tuple,)):
            doc_or_docs = [doc_or_docs]

        for doc in doc_or_docs:
            docid = doc['_id']
            new_doc = copy.deepcopy(doc)
            couchapp = doc.get('couchapp', {})
            if not couchapp:
                new_doc['couchapp'] = {}
                
            # we process attachments later
            del new_doc['_attachments']
            if 'signatures' in new_doc['couchapp']:
                del new_doc['couchapp']['signatures']
                
            for db in dbs: 
                if docid in db:
                    try:
                        current = db.get(docid)
                    except ResourceNotFound:
                        current = {}
                    _app_meta = current.get('couchapp', {})

                    if docid.startswith('_design'):
                        new_doc['couchapp'] ['signatures'] = _app_meta.get('signatures', {})
                        new_doc['_attachments'] = current.get('_attachments', {})
                    
                    if '_rev' in current:
                        new_doc['_rev'] = current.get('_rev')
                        
                if not atomic:
                    db[docid] = new_doc
                    if docid.startswith('_design/'):
                        self.send_attachments(db, doc, verbose=verbose)
                else:
                    if docid.startswith('_design/'):
                        self.encode_attachments(db, doc, new_doc, verbose=verbose)
                    db[docid] = new_doc
            
    def _put_attachment(self, db, doc, content, filename, content_length=None, 
            verbose=False):

        if hasattr(content, 'read') and content_length is None:
            content = content.read()

        nb_try = 0
        while True:
            error = False
            try:
                db.put_attachment(doc, content, filename, content_length=content_length)
            except (socket.error, httplib.BadStatusLine):
                time.sleep(0.4)
                error = True

            nb_try = nb_try +1
            if not error:
                break

            if nb_try > 3:
                if verbose >= 2:
                    print >>sys.stderr, "%s file not uploaded, sorry." % filename
                break
            
    def encode_attachments(self, db, design_doc,new_doc, verbose=False):
        # init vars
        all_signatures = {}                  
        if not 'couchapp' in design_doc:
            design_doc['couchapp'] = {}
        
        _signatures = design_doc['couchapp'].get('signatures', {})
        _length = design_doc['couchapp'].get('length', {})
        _attachments = design_doc.get('_attachments', {})
        docid = design_doc['_id']
        
        attachments = _attachments.copy()
        current_design = {}
        try:
            current_design = db[docid]
        except ResourceNotFound:
            pass
            
        new_attachments = current_design.get('_attachments', {})
        metadata = current_design.get('couchapp', {})
        if 'signatures' in metadata:
            all_signatures = metadata['signatures'].copy()
            for filename in metadata['signatures'].iterkeys():
                if not filename not in _signatures:
                    del new_attachments[filename]
                    del all_signatures[filename]
                elif _signatures[filename] == metadata['signatures'][filename]:
                    del attachments[filename]

        for filename, value in attachments.iteritems():
            content_length = _length.get(filename, None)
            if verbose:
                print "Attaching %s (%s)" % (filename, content_length)
            
            with open(value, "rb") as f:
                new_attachments[filename] = {
                    "content_type": ';'.join(filter(None, mimetypes.guess_type(filename))),
                    "data": base64.b64encode(f.read()),
                }
                     
        # update signatures
        if not 'couchapp' in new_doc:
            new_doc['couchapp'] = {}

        all_signatures.update(_signatures)
        new_doc['couchapp'].update({'signatures': _signatures})
        new_doc['_attachments'] = new_attachments
                
    def send_attachments(self, db, design_doc, verbose=False):
        # init vars
        all_signatures = {}                  
        if not 'couchapp' in design_doc:
            design_doc['couchapp'] = {}
        
        _signatures = design_doc['couchapp'].get('signatures', {})
        _length = design_doc['couchapp'].get('length', {})
        _attachments = design_doc.get('_attachments', {})
        docid = design_doc['_id']
        
        # detect attachments to be removed and keep
        # only new version attachments to update.
        current_design = db[docid]
        metadata = current_design.get('couchapp', {})
        attachments = _attachments.copy()
        if 'signatures' in metadata:
            all_signatures = metadata['signatures'].copy()
            for filename in metadata['signatures'].iterkeys():
                if filename not in _signatures:
                    db.delete_attachment(current_design, filename)
                elif _signatures[filename] == metadata['signatures'][filename]:
                    del attachments[filename]

        for filename, value in attachments.iteritems():
            content_length = _length.get(filename, None)
            if verbose:
                print "Attaching %s (%s)" % (filename, content_length)
            
            with open(value, "rb") as f:
                # fix issue with httplib that raises BadStatusLine
                # error because it didn't close the connection
                self._put_attachment(db, current_design, f, filename, 
                    content_length=content_length, verbose=verbose)
                     
        # update signatures
        current_design = db[docid]
        if not 'couchapp' in current_design:
            current_design['couchapp'] = {}

        all_signatures.update(_signatures)
        current_design['couchapp'].update({'signatures': all_signatures})
        db[docid] = current_design

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
            designpath = [designpath]
        docpath = docpath or []
        if isinstance(docpath, basestring):
            docpath = [docpath]
            
        self.designpath = list(designpath)
        self.docpath = list(docpath)
        
    def get_docs(self, verbose=False):
        docs = []
        for docpath in self.docpath:
            if not os.path.isdir(docpath):
                raise DocsPathNotFound("%s doesn't exist" % docpath)
            for name in os.listdir(docpath):
                if name.startswith('.'):
                    continue
                elif os.path.isfile(name):
                    fpath = os.path.join(docpath, name)
                    try:
                        doc = read_file(fpath)
                    except UnicodeDecodeError, e:
                        print >>sys.stderr, str(e)
                        raise
                        
                    if name.endswith('.json'):
                        try:
                            doc = read_json(fpath)
                        except ValueError:
                            pass
                    doc.update({ '_id': name })
                    docs.append(doc)
                else:
                    doc = { '_id': name }
                    manifest = []
                    app_dir = os.path.join(docpath, name)
                    doc.update(self.dir_to_fields(app_dir, app_dir, 
                        manifest=manifest, verbose=verbose))
                    if not 'couchapp' in doc:
                        doc['couchapp'] = {}
                    doc['couchapp'].update({ 'manifest': manifest })
                    docs.append(doc)
                    
        for designpath in self.designpath:
            if not os.path.isdir(designpath):
                raise DocsPathNotFound("%s doesn't exist" % designpath)
            for name in os.listdir(designpath):
                ddoc = self.get_designdoc(designpath, name, verbose=verbose)
                if ddoc:
                    docs.append(ddoc)
                
        return docs
        
    def get_designdoc(self, root, name, design_name=None, verbose=False):
        design_doc = {}
        if not name.startswith('.') and not os.path.isfile(name):
            manifest = []
            objects = {}
            if design_name is None:
                docid = design_doc['_id'] = "_design/%s" % name
            else:
                docid = design_doc['_id'] = "_design/%s" % design_name
            app_dir = os.path.join(root, name)
            attach_dir = os.path.join(app_dir, '_attachments')

            design_doc.update(self.dir_to_fields(app_dir, manifest=manifest,
                    verbose=verbose))

            if not 'couchapp' in design_doc:
                design_doc['couchapp'] = {}

            for funs in ['shows', 'lists', 'updates', 'filters']:
                if funs in design_doc:
                    package_shows(design_doc, design_doc[funs], app_dir, objects, verbose=verbose)

            if 'views' in design_doc:
                # clean views
                # we remove empty views and malformed from the list
                # of pushed views. We also clean manifest
                views = {}
                dmanifest = {}
                for i, fname in enumerate(manifest):
                    if fname.startswith("views/") and fname != "views/":
                        name, ext = os.path.splitext(fname)
                        if name.endswith('/'):
                            name = name[:-1]
                        dmanifest[name] = i

                for vname, value in design_doc['views'].iteritems():
                    if value and isinstance(value, dict):
                        views[vname] = value
                    else:
                        del manifest[dmanifest["views/%s" % vname]]
                design_doc['views'] = views
                package_views(design_doc, design_doc["views"], app_dir, objects, verbose=verbose)

            couchapp = design_doc.get('couchapp', False)
            design_doc.update({
                'couchapp': {
                    'manifest': manifest,
                    'objects': objects
                }
            })
            self.attach(design_doc, attach_dir, docid, verbose=verbose)
            self.attach_vendors(design_doc, app_dir, docid, verbose=verbose)
        return design_doc
            
    def dir_to_fields(self, app_dir, current_dir='', depth=0,
            manifest=[], verbose=False):
        fields={}
        if not current_dir:
            current_dir = app_dir
        for name in os.listdir(current_dir):
            current_path = os.path.join(current_dir, name)
            rel_path = relpath(current_path, app_dir)
            if name.startswith('.'):
                continue
            elif name.startswith('_'):
                # files starting with "_" are always "special"
                continue
            elif depth == 0 and name in ('couchapp', 'couchapp.json'):
                # we are in app_meta
                if name == "couchapp":
                    manifest.append('%s/' % rel_path)
                    content = self.dir_to_fields(app_dir, current_path,
                        depth=depth+1, manifest=manifest)
                else:
                    manifest.append(rel_path)
                    content = read_json(current_path)
                    if not isinstance(content, dict):
                        content = { "meta": content }
                if 'signatures' in content:
                    del content['signatures']

                if 'manifest' in content:
                    del content['manifest']

                if 'objects' in content:
                    del content['objects']

                if 'couchapp' in fields:
                    fields['couchapp'].update(content)
                else:
                    fields['couchapp'] = content
            elif os.path.isdir(current_path):
                manifest.append('%s/' % rel_path)
                fields[name] = self.dir_to_fields(app_dir, current_path,
                        depth=depth+1, manifest=manifest,
                        verbose=verbose)
            else:
                if verbose >= 2:
                    print >>sys.stderr, "push %s" % rel_path                
                content = ''
                try:
                    content = read_file(current_path)
                except UnicodeDecodeError, e:
                    if verbose >= 2:
                        print >>sys.stderr, "%s isn't encoded in utf8" % current_path
                    content = self.ui.read(current_path, utf8=False)
                    try:
                        content.encode('utf-8')
                    except UnicodeError, e:
                        print >>sys.stderr, "plan B didn't work, %s is a binary" % current_path
                        print >>sys.stderr, "use plan C: encode to base64"
                        content = "base64-encoded;%s" % base64.b64encode(content)
                        
                if name.endswith('.json'):
                    try:
                        content = anyjson.deserialize(content)
                    except ValueError:
                        if verbose >= 2:
                            print >>sys.stderr, "Json invalid in %s" % current_path
                
                # remove extension
                name, ext = os.path.splitext(name)
                if name in fields:
                    if verbose >= 2:
                        print >>sys.stderr, "%(name)s is already in properties. Can't add (%(name)s%(ext)s)" % {
                        "name": name,
                        "ext": ext
                        }
                else:
                    manifest.append(rel_path)
                    fields[name] = content
        return fields
        
    def attach_vendors(self, design_doc, app_dir,  docid, verbose):
        vendor_dir = os.path.join(app_dir, 'vendor')
        if not os.path.isdir(vendor_dir):
            return
            
        for name in os.listdir(vendor_dir):
            current_path = os.path.join(vendor_dir, name)
            if os.path.isdir(current_path):
                attach_dir = os.path.join(current_path, '_attachments')
                if os.path.isdir(attach_dir):
                    self.attach(design_doc, attach_dir, docid, verbose, 
                                    vendor=name)

    def attach(self, doc, attach_dir, docid, verbose=False, vendor=None):
        # get attachments
        _signatures = {}
        _attachments = {}
        _length = {}
        all_signatures = {}
        for root, dirs, files in os.walk(attach_dir):
            if files:
                for filename in files:
                    if filename.startswith('.'):
                        continue
                    else:
                        file_path = os.path.join(root, filename)
                        name = relpath(file_path, attach_dir)
                        if vendor is not None:
                            name = os.path.join('vendor', vendor, name)
                        _signatures[name] = sign_file(file_path)
                        _attachments[name] = file_path
                        _length[name] = int(os.path.getsize(file_path))
        
        for prop in ('couchapp', '_attachments'):
            if not prop in doc:
                doc[prop] = {}
            
        if not 'signatures' in doc['couchapp']:
            doc['couchapp']['signatures'] = {}
            
        if not 'length' in doc['couchapp']:
            doc['couchapp']['length'] = {}
            
        doc['_attachments'].update(_attachments)
        doc['couchapp']['signatures'].update(_signatures)
        doc['couchapp']['length'].update(_length)
        
class FileSystemDocLoader(FileSystemDocsLoader):
    """ Load only one design doc from a path on the filesystem.
        
        >>> loader = FileSystemDocLoader("/path/to/designdocfolder", "nameodesigndoc")
    """
    
    def __init__(self, designpath, name, design_name=None):
        self.designpath = designpath
        self.name = name
        self.design_name = design_name
        
    def get_docs(self, verbose=False):
        docs = []
        ddoc = self.get_designdoc(self.designpath, self.name, 
                      design_name=self.design_name, verbose=verbose)
        if ddoc:
            docs.append(ddoc)
        return docs
