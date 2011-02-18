# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

from __future__ import with_statement
import base64
import copy
from hashlib import md5
import logging
import mimetypes
import os
import os.path
import re

from .. import client
from ..exceptions import ResourceNotFound, DesignerError, \
BulkSaveError
from .macros import package_shows, package_views
from .. import utils

if os.name == 'nt':
    def _replace_backslash(name):
        return name.replace("\\", "/")

    def _replace_slash(name):
        return name.replace("/", "\\")
else:
    def _replace_backslash(name):
        return name

    def _replace_slash(name):
        return name

logger = logging.getLogger(__name__)

class FSDoc(object):
    
    def __init__(self, path, create=False, docid=None, is_ddoc=True):
        self.docdir = path
        self.ignores = []
        self.is_ddoc = is_ddoc
        
        ignorefile = os.path.join(path, '.couchappignore')
        if os.path.exists(ignorefile):
            # A .couchappignore file is a json file containing a
            # list of regexps for things to skip
            self.ignores = utils.json.load(open(ignorefile, 'r'))
        if not docid:
            docid = self.get_id()
        self.docid = docid
        self._doc = {'_id': self.docid}
        if create: 
            self.create()
        
    def get_id(self):
        """
        if there is an _id file, docid is extracted from it,
        else we take the current folder name.
        """
        idfile = os.path.join(self.docdir, '_id')
        if os.path.exists(idfile):
            docid = utils.read_file(idfile).split("\n")[0].strip()
            if docid: return docid
        if self.is_ddoc:
            return "_design/%s" % os.path.split(self.docdir)[1]
        else:
            return os.path.split(self.docdir)[1]
        
    def __repr__(self):
        return "<%s (%s/%s)>" % (self.__class__.__name__, self.docdir, self.docid)
        
    def __str__(self):
        return utils.json.dumps(self.doc())
        
    def create(self):
        if not os.path.isdir(self.docdir):
            logger.error("%s directory doesn't exist." % self.docdir)
            
        rcfile = os.path.join(self.docdir, '.couchapprc')
        if not os.path.isfile(rcfile):
            utils.write_json(rcfile, {})
        else:
            logger.warning("CouchApp already initialized in %s." % self.docdir)

    def push(self, dbs, atomic=True, force=False):
        """Push a doc to a list of database `dburls`. If noatomic is true
        each attachments will be sent one by one."""
        for db in dbs:
            if not atomic:
                doc = self.doc(db, force=force)
                db.save_doc(doc, force_update=True)
            else:
                doc = self.doc(db, with_attachments=False, force=force)
                db.save_doc(doc, force_update=True)
                
                attachments = doc.get('_attachments') or {}

                for name, filepath in self.attachments():
                    if name not in attachments:
                        logger.debug("attach %s " % name)
                        db.put_attachment(doc, open(filepath, "r"), 
                                            name=name)
            
            logger.debug("%s/%s had been pushed from %s" % (db.uri,
                self.docid, self.docdir))


    def attachment_stub(self, name, filepath):
        att = {}
        with open(filepath, "rb") as f:
            re_sp = re.compile('\s')
            att = {
                    "data": re_sp.sub('',base64.b64encode(f.read())),
                    "content_type": ';'.join(filter(None, 
                                            mimetypes.guess_type(name)))
            }

        return att 

    def doc(self, db=None, with_attachments=True, force=False):
        """ Function to reetrieve document object from
        document directory. If `with_attachments` is True
        attachments will be included and encoded"""
        
        manifest = []
        objects = {}
        signatures = {}
        attachments = {}

        self._doc = {'_id': self.docid}
        
        # get designdoc
        self._doc.update(self.dir_to_fields(self.docdir, manifest=manifest))
        
        if not 'couchapp' in self._doc:
            self._doc['couchapp'] = {}

        self.olddoc = {}
        if db is not None:
            try:
                self.olddoc = db.open_doc(self._doc['_id'])
                attachments = self.olddoc.get('_attachments') or {}
                self._doc.update({'_rev': self.olddoc['_rev']})
            except ResourceNotFound:
                self.olddoc = {}
        
        if 'couchapp' in self.olddoc:
            old_signatures = self.olddoc['couchapp'].get('signatures', 
                                                        {})
        else:
            old_signatures = {}
        
        for name, filepath in self.attachments():
            signatures[name] = utils.sign_file(filepath)
            if with_attachments and not old_signatures:
                logger.debug("attach %s " % name)
                attachments[name] = self.attachment_stub(name, filepath) 

        if old_signatures:
            for name, signature in old_signatures.items():
                cursign = signatures.get(name)
                if not cursign:
                    logger.debug("detach %s " % name)
                    del attachments[name]
                elif cursign != signature:
                    logger.debug("detach %s " % name)
                    del attachments[name]
                else:
                    continue
            
            if with_attachments:
                for name, filepath in self.attachments():
                    if old_signatures.get(name) != signatures.get(name) or force:
                        logger.debug("attach %s " % name)
                        attachments[name] = self.attachment_stub(name, filepath) 
        
        self._doc['_attachments'] = attachments
            
        self._doc['couchapp'].update({
            'manifest': manifest,
            'objects': objects,
            'signatures': signatures
        })
        
        
        if self.docid.startswith('_design/'):  # process macros
            for funs in ['shows', 'lists', 'updates', 'filters', 
                    'spatial']:
                if funs in self._doc:
                    package_shows(self._doc, self._doc[funs], self.docdir, 
                            objects)
            
            if 'validate_doc_update' in self._doc:
                tmp_dict = dict(validate_doc_update=self._doc[
                                                    "validate_doc_update"])
                package_shows( self._doc, tmp_dict, self.docdir, 
                    objects)
                self._doc.update(tmp_dict)

            if 'views' in  self._doc:
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
            
                for vname, value in self._doc['views'].iteritems():
                    if value and isinstance(value, dict):
                        views[vname] = value
                    else:
                        del manifest[dmanifest["views/%s" % vname]]
                self._doc['views'] = views
                package_views(self._doc,self._doc["views"], self.docdir, 
                        objects)
            
            if "fulltext" in self._doc:
                package_views(self._doc,self._doc["fulltext"], self.docdir, 
                        objects)

            
        return self._doc
    
    def check_ignore(self, item):
        for i in self.ignores:
            match = re.match(i, item)
            if match:
                logger.debug("ignoring %s" % item)
                return True
        return False
    
    def dir_to_fields(self, current_dir='', depth=0,
                manifest=[]):
        """ process a directory and get all members """        
        
        fields={}
        if not current_dir:
            current_dir = self.docdir
        for name in os.listdir(current_dir):
            current_path = os.path.join(current_dir, name)
            rel_path = _replace_backslash(utils.relpath(current_path, self.docdir))
            if name.startswith("."):
                continue
            elif self.check_ignore(name):
                continue
            elif depth == 0 and name.startswith('_'):
                # files starting with "_" are always "special"
                continue
            elif name == '_attachments':
                continue
            elif depth == 0 and (name == 'couchapp' or name == 'couchapp.json'):
                # we are in app_meta
                if name == "couchapp":
                    manifest.append('%s/' % rel_path)
                    content = self.dir_to_fields(current_path,
                        depth=depth+1, manifest=manifest)
                else:
                    manifest.append(rel_path)
                    content = utils.read_json(current_path)
                    if not isinstance(content, dict):
                        content = { "meta": content }
                if 'signatures' in content:
                    del content['signatures']

                if 'manifest' in content:
                    del content['manifest']

                if 'objects' in content:
                    del content['objects']
                
                if 'length' in content:
                    del content['length']

                if 'couchapp' in fields:
                    fields['couchapp'].update(content)
                else:
                    fields['couchapp'] = content
            elif os.path.isdir(current_path):
                manifest.append('%s/' % rel_path)
                fields[name] = self.dir_to_fields(current_path,
                        depth=depth+1, manifest=manifest)
            else:
                logger.debug("push %s" % rel_path)
                  
                content = ''  
                if name.endswith('.json'):
                    try:
                        content = utils.read_json(current_path)
                    except ValueError:
                        logger.error("Json invalid in %s" % current_path)           
                else:
                    try:
                        content = utils.read_file(current_path).strip()
                    except UnicodeDecodeError:
                        logger.warning("%s isn't encoded in utf8" % current_path)
                        content = utils.read_file(current_path, utf8=False)
                        try:
                            content.encode('utf-8')
                        except UnicodeError:
                            logger.warning(
                            "plan B didn't work, %s is a binary" % current_path)
                            logger.warning("use plan C: encode to base64")   
                            content = "base64-encoded;%s" % base64.b64encode(
                                                                        content)

                
                # remove extension
                name, ext = os.path.splitext(name)
                if name in fields:
                    logger.warning(
        "%(name)s is already in properties. Can't add (%(fqn)s)" % {
                            "name": name, "fqn": rel_path })
                else:
                    manifest.append(rel_path)
                    fields[name] = content
        return fields
        
    def _process_attachments(self, path, vendor=None):
        """ the function processing directory to yeld
        attachments. """
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for dirname in dirs:
                    if dirname.startswith('.'):
                        dirs.remove(dirname)
                    elif self.check_ignore(dirname):
                        dirs.remove(dirname)
                if files:
                    for filename in files:
                        if filename.startswith('.'):
                            continue
                        elif self.check_ignore(filename):
                            continue
                        else:
                            filepath = os.path.join(root, filename)
                            name = utils.relpath(filepath, path)
                            if vendor is not None:
                                name = os.path.join('vendor', vendor, name)
                            name = _replace_backslash(name)
                            yield (name, filepath)
                
    def attachments(self):
        """ This function yield a tuple (name, filepath) corresponding
        to each attachment (vendor included) in the couchapp. `name`
        is the name of attachment in `_attachments` member and `filepath`
        the path to the attachment on the disk.
        
        attachments are processed later to allow us to send attachments inline
        or one by one.
        """
        # process main attachments
        attachdir = os.path.join(self.docdir, "_attachments")
        for attachment in self._process_attachments(attachdir):
            yield attachment
        vendordir = os.path.join(self.docdir, 'vendor')
        if not os.path.isdir(vendordir):
            logger.debug("%s don't exist" % vendordir)
            return
            
        for name in os.listdir(vendordir):
            current_path = os.path.join(vendordir, name)
            if os.path.isdir(current_path):
                attachdir = os.path.join(current_path, '_attachments')
                if os.path.isdir(attachdir):
                    for attachment in self._process_attachments(attachdir, 
                                                        vendor=name):
                        yield attachment
    
    def index(self, dburl, index):
        if index is not None:
            return "%s/%s/%s" % (dburl, self.docid, index)
        elif os.path.isfile(os.path.join(self.docdir, "_attachments", 
                    'index.html')):
            return "%s/%s/index.html" % (dburl, self.docid)
        return False
        
def document(path, create=False, docid=None, is_ddoc=True):
    """ simple function to retrive a doc object from filesystem """
    return FSDoc(path, create=create, docid=docid, is_ddoc=is_ddoc)

def push(path, dbs, atomic=True, force=False, docid=None):
    """ push a document from the fs to one or more dbs. Identic to
    couchapp push command """
    if not isinstance(dbs, (list, tuple)):
        dbs = [dbs]
            
    doc = document(path, create=False, docid=docid)
    doc.push(dbs, atomic=atomic, force=force)
    docspath = os.path.join(path, '_docs')
    if os.path.exists(docspath):
        pushdocs(docspath, dbs, atomic=atomic)

def pushapps(path, dbs, atomic=True, export=False, couchapprc=False):
    """ push all couchapps in one folder like couchapp pushapps command
    line """
    if not isinstance(dbs, (list, tuple)):
        dbs = [dbs]
    
    apps = []
    for d in os.listdir(path):
        appdir = os.path.join(path, d)
        if os.path.isdir(appdir):
            if couchapprc and not os.path.isfile(os.path.join(appdir, 
                '.couchapprc')):
                continue
            doc = document(appdir)
            if not atomic:
                doc.push(dbs, atomic=False)
            else:
                apps.append(doc)
    if apps:
        if export:
            docs= [doc.doc() for doc in apps]
            jsonobj = {'docs': docs}
            return jsonobj
        else:
            for db in dbs:
                docs = []
                docs = [doc.doc(db) for doc in apps]
                try:
                    db.save_docs(docs)
                except BulkSaveError, e:
                    docs1 = []
                    for doc in e.errors:
                        try:
                            doc['_rev'] = db.last_rev(doc['_id'])
                            docs1.append(doc)
                        except ResourceNotFound:
                            pass 
                    if docs1:
                        db.save_docs(docs1)


def pushdocs(path, dbs, atomic=True, export=False):
    """ push multiple docs in a path """
    if not isinstance(dbs, (list, tuple)):
        dbs = [dbs]

    docs = []
    for d in os.listdir(path):
        docdir = os.path.join(path, d)
        if docdir.startswith('.'):
            continue
        elif os.path.isfile(docdir):
            if d.endswith(".json"):
                doc = utils.read_json(docdir)
                docid, ext = os.path.splitext(d)
                doc.setdefault('_id', docid)
                doc.setdefault('couchapp', {})
                if not atomic:
                    for db in dbs:
                        db.save_doc(doc, force_update=True)
                else:
                    docs.append(doc)
        else:
            doc = document(docdir, is_ddoc=False)
            if not atomic:
                doc.push(dbs, atomic=False)
            else:
                docs.append(doc)
    if docs:
        if export:
            docs1 = []
            for doc in docs:
                if hasattr(doc, 'doc'):
                    docs1.append(doc.doc())
                else:
                    docs1.append(doc)
            jsonobj = {'docs': docs1}
            return jsonobj
        else:
            for db in dbs:
                docs1 = []
                for doc in docs:
                    if hasattr(doc, 'doc'):
                        docs1.append(doc.doc(db))
                    else:
                        newdoc = doc.copy()
                        try:
                            rev = db.last_rev(doc['_id'])
                            newdoc.update({'_rev': rev})
                        except ResourceNotFound:
                            pass
                        docs1.append(newdoc)
                try:
                    db.save_docs(docs1)
                except BulkSaveError, e:
                    # resolve conflicts
                    docs1 = []
                    for doc in e.errors:
                        try:
                            doc['_rev'] = db.last_rev(doc['_id'])
                            docs1.append(doc)
                        except ResourceNotFound:
                            pass 
                if docs1:
                    db.save_docs(docs1)

def clone(db, docid, dest=None, rev=None):
    """
    Clone a CouchDB document to the fs.
    
    """
    if not dest:
        dest = docid
   
    path = os.path.normpath(os.path.join(os.getcwd(), dest))
    if not os.path.exists(path):
        os.makedirs(path)

    if not rev:
        doc = db.open_doc(docid)
    else:
        doc = db.open_doc(docid, rev=rev)
    docid = doc['_id']
        
    
    metadata = doc.get('couchapp', {})
    
    # get manifest
    manifest = metadata.get('manifest', {})

    # get signatures
    signatures = metadata.get('signatures', {})

    # get objects refs
    objects = metadata.get('objects', {})

    # create files from manifest
    if manifest:
        for filename in manifest:
            logger.debug("clone property: %s" % filename)
            filepath = os.path.join(path, filename)
            if filename.endswith('/'): 
                if not os.path.isdir(filepath):
                    os.makedirs(filepath)
            elif filename == "couchapp.json":
                continue
            else:
                parts = utils.split_path(filename)
                fname = parts.pop()
                v = doc
                while 1:
                    try:
                        for key in parts:
                            v = v[key]
                    except KeyError:
                        break
                    # remove extension
                    last_key, ext = os.path.splitext(fname)

                    # make sure key exist
                    try:
                        content = v[last_key]
                    except KeyError:
                        break


                    if isinstance(content, basestring):
                        _ref = md5(utils.to_bytestring(content)).hexdigest()
                        if objects and _ref in objects:
                            content = objects[_ref]
                            
                        if content.startswith('base64-encoded;'):
                            content = base64.b64decode(content[15:])

                    if fname.endswith('.json'):
                        content = utils.json.dumps(content).encode('utf-8')

                    del v[last_key]

                    # make sure file dir have been created
                    filedir = os.path.dirname(filepath)
                    if not os.path.isdir(filedir):
                        os.makedirs(filedir)
                    
                    utils.write_content(filepath, content)

                    # remove the key from design doc
                    temp = doc
                    for key2 in parts:
                        if key2 == key:
                            if not temp[key2]:
                                del temp[key2]
                            break
                        temp = temp[key2]
                        
    
    # second pass for missing key or in case
    # manifest isn't in app
    for key in doc.iterkeys():
        if key.startswith('_'): 
            continue
        elif key in ('couchapp'):
            app_meta = copy.deepcopy(doc['couchapp'])
            if 'signatures' in app_meta:
                del app_meta['signatures']
            if 'manifest' in app_meta:
                del app_meta['manifest']
            if 'objects' in app_meta:
                del app_meta['objects']
            if 'length' in app_meta:
                del app_meta['length']
            if app_meta:
                couchapp_file = os.path.join(path, 'couchapp.json')
                utils.write_json(couchapp_file, app_meta)
        elif key in ('views'):
            vs_dir = os.path.join(path, key)
            if not os.path.isdir(vs_dir):
                os.makedirs(vs_dir)
            for vsname, vs_item in doc[key].iteritems():
                vs_item_dir = os.path.join(vs_dir, vsname)
                if not os.path.isdir(vs_item_dir):
                    os.makedirs(vs_item_dir)
                for func_name, func in vs_item.iteritems():
                    filename = os.path.join(vs_item_dir, '%s.js' % 
                            func_name)
                    utils.write_content(filename, func)
                    logger.warning("clone view not in manifest: %s" % filename)
        elif key in ('shows', 'lists', 'filter', 'update'):
            showpath = os.path.join(path, key)
            if not os.path.isdir(showpath):
                os.makedirs(showpath)
            for func_name, func in doc[key].iteritems():
                filename = os.path.join(showpath, '%s.js' % 
                        func_name)
                utils.write_content(filename, func)
                logger.warning(
                    "clone show or list not in manifest: %s" % filename)
        else:
            filedir = os.path.join(path, key)
            if os.path.exists(filedir):
                continue
            else:
                logger.warning("clone property not in manifest: %s" % key)
                if isinstance(doc[key], (list, tuple,)):
                    utils.write_json(filedir + ".json", doc[key])
                elif isinstance(doc[key], dict):
                    if not os.path.isdir(filedir):
                        os.makedirs(filedir)
                    for field, value in doc[key].iteritems():
                        fieldpath = os.path.join(filedir, field)
                        if isinstance(value, basestring):
                            if value.startswith('base64-encoded;'):
                                value = base64.b64decode(content[15:])
                            utils.write_content(fieldpath, value)
                        else:
                            utils.write_json(fieldpath + '.json', value)        
                else:
                    value = doc[key]
                    if not isinstance(value, basestring):
                        value = str(value)
                    utils.write_content(filedir, value)

    # save id
    idfile = os.path.join(path, '_id')
    utils.write_content(idfile, doc['_id'])
  
    utils.write_json(os.path.join(path, '.couchapprc'), {})

    if '_attachments' in doc:  # process attachments
        attachdir = os.path.join(path, '_attachments')
        if not os.path.isdir(attachdir):
            os.makedirs(attachdir)
            
        for filename in doc['_attachments'].iterkeys():
            if filename.startswith('vendor'):
                attach_parts = utils.split_path(filename)
                vendor_attachdir = os.path.join(path, attach_parts.pop(0),
                        attach_parts.pop(0), '_attachments')
                filepath = os.path.join(vendor_attachdir, *attach_parts)
            else:
                filepath = os.path.join(attachdir, filename)
            filepath = _replace_slash(filepath)
            currentdir = os.path.dirname(filepath)
            if not os.path.isdir(currentdir):
                os.makedirs(currentdir)
    
            if signatures.get(filename) != utils.sign_file(filepath):
                resp = db.fetch_attachment(docid, filename, stream=True)
                with open(filepath, 'wb') as f:
                    for chunk in resp.body_stream():
                        f.write(chunk)
                logger.debug("clone attachment: %s" % filename)
                
    logger.debug("%s/%s cloned in %s" % (db.uri, docid, dest))

def clone_design_doc(source, dest, rev=None):
    """ Clone a design document from it's url like couchapp does.
    """
    try:
        dburl, docid = source.split('_design/')
    except ValueError:
        raise DesignerError("%s isn't a valid source" % source)

    db = client.Database(dburl[:-1], create=False)    
    clone(db, docid, dest, rev=rev)
