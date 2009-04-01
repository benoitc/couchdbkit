# -*- coding: utf-8 -*-
# Copyright 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import base64
import cgi
from itertools import groupby
from mimetypes import guess_type
import re

from couchdbkit.resource import ResourceNotFound
from couchdbkit.utils import validate_dbname
from couchdbkit.client.view import View, TempView



__all__ = ['InvalidAttachment', 'Database']
class InvalidAttachment(Exception):
    """ raised when an attachment is invalid """

class Database(object):
    """ Object that abstract access to a CouchDB database
    A Database object could act as a Dict object.
    """

    def __init__(self, server, dbname):
        """Constructor for Database

        :param server: Server instance
        :param dbname: str, name of database
        """

        if not hasattr(server, 'next_uuid'):
            raise TypeError('%s is not a couchdbkit.server instance' % 
                            server.__class__.__name__)
                            
        self.dbname = validate_dbname(dbname)
        self.server = server
        self.res = server.res.clone()
        self.res.update_uri('/%s' % dbname)
        
    def info(self):
        """
        Get infos of database
            
        :return: dict
        """
        data = self.res.get()
        return data
        
    def compact(self):
        """ compact database"""
        res = self.res.post('/_compact')
        
    def doc_exist(self, docid):
        """Test if document exist in database

        :param docid: str, document id
        :return: boolean, True if document exist
        """

        try:
            data = self.res.head(docid)
        except ResourceNotFound:
            return False
        return True
        
    def get(self, docid, rev=None, wrapper=None):
        """Get document from database
        
        Args:
        :param docid: str, document id to retrieve 
        :param rev: if specified, allow you to retrieve
        a specifiec revision of document
        :param wrapper: callable. function that take a dict as param. 
        Used to wrap an object.
        
        :return: dict, representation of CouchDB document as
         a dict.
        """
        self.escape_docid(docid)
        if rev is not None:
            doc = self.res.get(docid, rev=rev)
        else:
            doc = self.res.get(docid)

        if wrapper is not None:
            if not callable(wrapper):
                raise TypeError("wrapper isn't a callable")
            return wrapper(doc)
            
        return doc
        
    def doc_revisions(self, docid, with_doc=True):
        """ retrieve revisions of a doc
            
        :param docid: str, id of document
        :param with_doc: bool, if True return document
        dict with revisions as member, if false return 
        only revisions
        
        :return: dict: '_rev_infos' member if you have set with_doc
        to True :

        .. code-block:: python

                {
                    "_revs_info": [
                        {"rev": "123456", "status": "disk"},
                            {"rev": "234567", "status": "missing"},
                            {"rev": "345678", "status": "deleted"},
                    ]
                }
            
        If False, return current revision of the document, but with
        an additional field, _revs, the value being a list of 
        the available revision IDs. 
        """
        self.escape_docid(docid)
        try:
            if with_doc:
                doc_with_rev = self.res.get(docid, revs=True)
            else:
                doc_with_revs = self.res.get(docid, revs_info=True)
        except ResourceNotFound:
            return None
        return doc_with_revs           
        
    def save_doc(self, doc):
        """ Save a document. It will use the `_id` member of the document 
        or request a new uuid from CouchDB. IDs are attached to
        documents on the client side because POST has the curious property of
        being automatically retried by proxies in the event of network
        segmentation and lost responses. (Idee from `Couchrest <http://github.com/jchris/couchrest/>`)

        :param doc: dict 

        :return: dict or list of dict: dict or list are updated 
        with doc '_id' and '_rev' properties returned 
        by CouchDB server.

        """
        if doc is None:
            doc = {}
            
        if '_attachments' in doc:
            doc['_attachments'] = self.encode_attachments(doc['_attachments'])
            
        if '_id' in doc:
            self.escape_docid(doc['_id'])
            res = self.res.put(doc['_id'], payload=doc)
        else:
            try:
                doc['_id'] = self.server.next_uuid()
                res = self.res.put(doc['_id'], payload=doc)
            except:
                res = self.res.post(payload=doc)
        doc.update({ '_id': res['id'], '_rev': res['rev']})
        
    def bulk_save(self, docs, use_uuids=True, all_or_nothing=False):
        """ bulk save. Modify Multiple Documents With a Single Request
        
        :attr docs: list of docs
        :attr use_uuids: add _id in doc who don't have it already set.
        :attr all_or_nothing: In the case of a power failure, when the database 
        restarts either all the changes will have been saved or none of them. 
        However, it does not do conflict checking, so the documents will 
        be committed even if this creates conflicts.
        
        .. seealso:: `HTTP Bulk Document API <http://wiki.apache.org/couchdb/HTTP_Bulk_Document_API>`
        
        """
        def is_id(doc):
            return '_id' in doc
            
        if use_uuids:
            ids = []
            noids = []
            for k, g in groupby(docs, is_id):
                if not k:
                    noids = list(g)
                else:
                    ids = list(g)
            
            uuid_count = max(len(noids), self.server.uuid_batch_count)
            for doc in noids:
                nextid = self.server.next_uuid(count=uuid_count)
                print doc
                if nextid:
                    doc['_id'] = nextid
                    
            # make sure we have a corret id
            for doc in ids:
                self.escape_docid(doc['_id'])
                    
        payload = { "docs": docs }
        if all_or_nothing:
            payload["all-or-nothing"] = True
            
        # update docs
        results = self.res.post('/_bulk_docs', payload=payload)
        for i, res in enumerate(results):
            docs[i].update({'_id': res['id'], '_rev': res['rev']})
    
    def bulk_delete(self, docs, all_or_nothing=False):
        """ bulk delete. 
        It add '_deleted' member to doc then use bulk_save to save them."""
        for doc in docs:
            doc['_deleted'] = True
        self.bulk_save(docs, use_uuids=False, all_or_nothing=all_or_nothing)
 
    def delete_doc(self, doc):
        """ delete a document or a list of document

        :param doc: str or dict,  docyment id or full doc.
        :return: dict like:
       
        .. code-block:: python

            {"ok":true,"rev":"2839830636"}
        """
        result = { 'ok': False }
        
        if isinstance(doc, dict):
            if not '_id' or not '_rev' in doc:
                raise KeyError('_id and _rev are required to delete a doc')
                
            self.escape_docid(doc['_id'])
            result = self.res.delete(doc['_id'], rev=doc['_rev'])
        elif isinstance(doc, basestring): # we get a docid
            data = self.res.head(doc)
            response = self.res.get_response()
            result = self.res.delete(doc, 
                    rev=response['etag'].strip('"'))
        return result
        
    def copy_doc(self, doc, dest=None):
        """ copy an existing document to a new id. If dest is None, a new uuid will be requested
        :attr doc: dict or string, document or document id
        :attr dest: basestring or dict. if _rev is specified in dict it will override the doc
        """
        if isinstance(doc, basestring):
            docid = doc
        else:
            if not '_id' in doc:
                raise KeyError('_id is required to copy a doc')
            docid = doc['_id']
        
        if dest is None:
            destinatrion = self.server.next_uuid(count=1)   
        elif isinstance(dest, basestring):
            if dest in self:
                dest = self.get(dest)['_rev']
                destination = "%s?rev=%s" % (dest['_id'], dest['_rev'])
            else:
                destination = dest
        elif isinstance(dest, dict):
            if '_id' in dest and '_rev' in dest and dest['_id'] in self:
                rev = dest['_rev']
                destination = "%s?rev=%s" % (dest['_id'], dest['_rev'])
            else:
                raise KeyError("dest doesn't exist or this not a document ('_id' or '_rev' missig).")
    
        if destination:
            result = self.res.copy('/%s' % docid, headers={ "Destination": str(destination) } )
            return result    
        return { 'ok': False}
            
        
    def view(self, view_name, obj=None, wrapper=None, **params):
        if view_name.startswith('/'):
            view_name = view_name[1:]
        if view_name == '_all_docs':
            view_path = view_name
        else:
            view_name = view_name.split('/')
            dname = view_name.pop(0)
            vname = '/'.join(view_name)
            view_path = '_design/%s/_view/%s' % (dname, vname)
        if obj is not None:
            if not hasattr(obj, 'wrap'):
                raise AttributeError(" no 'wrap' method found in obj %s)" % str(obj))
            wrapper = obj.wrap

        return View(self, view_path, wrapper=wrapper)(**params)

    def temp_view(self, design, obj=None,  wrapper=None, **params):
        if obj is not None:
            if not hasattr(obj, 'wrap'):
                raise AttributeError(" no 'wrap' method found in obj %s)" % str(obj))
            wrapper = obj.wrap
        return TempView(self, design, wrapper=wrapper)(**params)

    def documents(self, wrapper=None, **params):
        return View(self, '_all_docs', wrapper=wrapper, **params)
    iter_documents = documents    

    def put_attachment(self, doc, content, name=None, 
            content_type=None, content_length=None):
        """ Add attachement to a document.

        :param doc: dict, document object
        :param content: string or :obj:`File` object.
        :param name: name or attachment (file name).
        :param content_type: string, mimetype of attachment.
        If you don't set it, it will be autodetected.
        :param content_lenght: int, size of attachment.

        :return: bool, True if everything was ok.


        Example:
            
            >>> from simplecouchdb import server
            >>> server = server()
            >>> db = server.create_db('couchdbkit_test')
            >>> doc = { 'string': 'test', 'number': 4 }
            >>> db.save(doc)
            >>> text_attachment = u'un texte attaché'
            >>> db.put_attachment(doc, text_attachment, "test", "text/plain")
            True
            >>> file = db.fetch_attachment(doc, 'test')
            >>> result = db.delete_attachment(doc, 'test')
            >>> result['ok']
            True
            >>> db.fetch_attachment(doc, 'test')
            >>> del server['couchdbkit_test']
            {u'ok': True}
        """

        headers = {}
        headers.setdefault('Content-Type', 'text/plain')

        if name is None:
            if hasattr('content', name):
                name = content.name
            else:
                raise InvalidAttachment('You should provid a valid attachment name')

        if content_type is None:
            content_type = ';'.join(filter(None, guess_type(name)))

        if content_type:
            headers['Content-Type'] = content_type

        if content_length and content_length is not None:
            headers['Content-Length'] = content_length

        if hasattr(doc, 'to_json'):
            doc_ = doc.to_json()
        else:
            doc_ = doc

        res = self.res(doc_['_id']).put(name, payload=content, 
                headers=headers, rev=doc_['_rev'])

        if res['ok']:
            doc_.update({ '_rev': res['rev']})
        return res['ok']

    def delete_attachment(self, doc, name):
        """ delete attachement of documen

        :param doc: dict, document object in python
        :param name: name of attachement
    
        :return: dict, withm member ok setto True if delete was ok.
        """

        return self.res(doc['_id']).delete(name, rev=doc['_rev'])

    def fetch_attachment(self, id_or_doc, name):
        """ get attachment in document
        
        :param id_or_doc: str or dict, doc id or document dict
        :param name: name of attachment default: default result

        :return: str, attachment
        """

        if isinstance(id_or_doc, basestring):
            docid = id_or_doc
        else:
            docid = id_or_doc['_id']
      
        try:
            data = self.res(docid).get(name)
        except ResourceNotFound:
            return None
        return data
        
 
    def __len__(self):
        return self.info()['doc_count'] 
        
    def __contains__(self, docid):
        return self.doc_exist(docid)
        
    def __getitem__(self, id):
        return self.get(id)
        
    def __setitem__(self, docid, doc):
        res = self.res.put(docid, payload=doc)
        doc.update({ '_id': res['id'], '_rev': res['rev']})
        
    def __delitem__(self, docid):
       data = self.res.head(docid)
       result = self.res.delete(docid, 
               rev=self.res.get_response()['etag'].strip('"'))

    def __iter__(self):
        return self.iterdocuments()
        
    def __nonzero__(self):
        return (len(self) > 0)
        
    def escape_docid(self, docid):
        if docid.startswith('_design/'):
            docid = "_design/%s" % (cgi.escape(docid[8:]))
            
    def encode_attachments(self, attachments):
        for k, v in attachments.iteritems():
            if v.get('stub', False):
                continue
            else:
                re_sp = re.compile('\s')
                v['data'] = re_sp.sub('', base64.b64encode(v['data']))
        return attachments         