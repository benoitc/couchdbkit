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

import cgi
from mimetypes import guess_type

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

    def __init__(self, node, dbname):
        """Constructor for Database

        :param node: simplecouchdb.core.node instance
        :param dbname: str, name of database on this node
        """

        if not hasattr(node, 'compact_db'):
            raise TypeError('%s is not a couchdbkit.node instance' % 
                            node.__class__.__name__)
                            
        self.dbname = validate_dbname(dbname)
        self.node = node
        self.res = node.res.clone()
        self.res.update_uri('/%s' % dbname)

    def info(self):
        """
        Get infos of database
            
        :return: dict
        """
        data = self.res.get()
        return data
        
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
        
    def revisions(self, docid, with_doc=True):
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
        
    def save(self, doc_or_docs):
        """ Save one documents or multiple documents.

        :param doc: dict or list/tuple of dict.

        :return: dict or list of dict: dict or list are updated 
        with doc '_id' and '_rev' properties returned 
        by CouchDB node.

        """
        if doc_or_docs is None:
            doc_or_docs = {}
        if isinstance(doc_or_docs, (list, tuple,)):
            for doc in doc_or_docs:
                if '_id' in doc:
                    self.escape_docid(doc['_id'])
            results = self.res.post('_bulk_docs', payload={ "docs": doc_or_docs })
            for i, res in enumerate(results):
                doc_or_docs[i].update({ '_id': res['id'], '_rev': res['rev']})
        else: 
            if '_id' in doc_or_docs:
                self.escape_docid(doc_or_docs['_id'])
                res = self.res.put(doc_or_docs['_id'], payload=doc_or_docs)
            else:
                res = self.res.post(payload=doc_or_docs)
            doc_or_docs.update({ '_id': res['id'], '_rev': res['rev']})
 
    def delete(self, doc_or_docs):
        """ delete a document or a list of document

        :param doc_or_docs: list or str: doment id or list
        of documents or list with _id and _rev, optionnaly 
        _deleted member set to true. See _bulk_docs document
        on couchdb wiki.
        
        :return: list of doc or dict like:
       
        .. code-block:: python

            {"ok":true,"rev":"2839830636"}
        """
        result = { 'ok': False }
        
        if isinstance(doc_or_docs, (list, tuple,)):
            docs = []
            for doc in doc_or_docs:
                self.escape_docid(doc['_id'])
                doc.update({'_deleted': True})
                docs.append(doc)
            result = self.res.post('_bulk_docs', payload={
                "docs": docs })
        elif isinstance(doc_or_docs, dict) and '_id' in doc_or_docs:
            self.escape_docid(doc_or_docs['_id'])
            result = self.res.delete(doc_or_docs['_id'], rev=doc_or_docs['_rev'])
        elif isinstance(doc_or_docs, basestring):
            data = self.res.head(doc_or_docs)
            response = self.res.get_response()
            result = self.res.delete(doc_or_docs, 
                    rev=response['etag'].strip('"'))
        return result

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

    def documents(self, **params):
        return view.View(self, '_all_docs', wrapper=wrapper, **params)
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
            
            >>> from simplecouchdb import node
            >>> node = node()
            >>> db = node.create_db('couchdbkit_test')
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
            >>> del node['couchdbkit_test']
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
            docid = "_design/%s" % (cgi.escape(docid[7:]))