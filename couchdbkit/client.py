# -*- coding: utf-8 -*-
#
# Copyright (c) 2008-2009 Benoit Chesneau <benoitc@e-engura.com> 
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import base64
import cgi
from itertools import groupby
from mimetypes import guess_type
import re

from restclient.rest import url_quote

from couchdbkit.exceptions import *
from couchdbkit.resource import CouchdbResource, ResourceNotFound, ResourceConflict
from couchdbkit.utils import validate_dbname

DEFAULT_UUID_BATCH_COUNT = 1000

class Server(object):
    """ Server object that allow you to access and manage a couchdb node. 
    A Server object could be use like any `dict` object.
    """
    
    def __init__(self, uri='http://127.0.0.1:5984', uuid_batch_count=DEFAULT_UUID_BATCH_COUNT, 
            transport=None):
        """ constructor for Server object
        
        :attr uri: uri of CouchDb host
        :attr uuid_batch_count: max of uuids to get in one time
        :attr transport: an transport instance from :mod:`restclient.transport`. Could be used
                to manage authentification to your server or proxy.
        """
        
        if not uri or uri is None:
            raise ValueError("Server uri is missing")

        self.uri = uri
        self.transport = transport
        self.uuid_batch_count = uuid_batch_count
        self._uuid_batch_count = uuid_batch_count
        
        self.res = CouchdbResource(uri, transport=transport)
        self.uuids = []
        
    def info(self):
        """ info of server 
        :return: dict
        """
        return self.res.get()
    
    def all_dbs(self):
        """ get list of databases in CouchDb host """
        result = self.res.get('/_all_dbs')
        return result
        
    def create_db(self, dbname):
        """ Create a database on CouchDb host

        :param dname: str, name of db

        :return: Database instance if it's ok or dict message
        """
        
        if "/" in dbname:
            dbname = url_quote(dbname, safe=":")
        res = self.res.put('/%s/' % validate_dbname(dbname))
        if res['ok']:
            return Database(self, dbname)
        return res['ok']

    def get_or_create_db(self, dbname):
        try:
            return self[dbname]
        except ResourceNotFound:
            return self.create_db(dbname)
        
    def delete_db(self, dbname):
        if "/" in dbname:
            dbname = url_quote(dbname, safe=":")
        del self[dbname]
        
    def next_uuid(self, count=None):
        if count is not None:
            self._uuid_batch_count = count
        else:
            self._uuid_batch_count = self.uuid_batch_count
        
        self.uuids = self.uuids or []
        if not self.uuids:
            self.uuids = self.res.get('/_uuids', count=self._uuid_batch_count)["uuids"]
        return self.uuids.pop()
          
    def __getitem__(self, dbname):
        if dbname in self:
            return Database(self, dbname)
        raise ResourceNotFound
        
    def __delitem__(self, dbname):
        return self.res.delete('/%s/' % validate_dbname(dbname))
        
    def __contains__(self, dbname):
        if dbname in self.all_dbs():
            return True
        return False
        
    def __iter__(self):
        for dbname in self.all_dbs():
            yield Database(self, dbname)

    def __len__(self):
        return len(self.all_dbs())
        
    def __nonzero__(self):
        return (len(self) > 0)
        
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
    
    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.dbname)
        
    @classmethod
    def from_uri(cls, uri, dbname, uuid_batch_count=DEFAULT_UUID_BATCH_COUNT, 
                transport=None):
        """ Create a database from its url. """
        server_uri = uri.split(dbname)[0][:-1]
        server = Server(server_uri, uuid_batch_count=uuid_batch_count, 
            transport=transport)
        return cls(server, dbname)
        
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

    def flush(self):
        _design_docs = [self[i["id"]] for i in self.all_docs(startkey="_design", endkey="_design/"+u"\u9999")]
        self.server.delete_db(self.dbname)
        self.server.create_db(self.dbname)
        [i.pop("_rev") for i in _design_docs]
        self.bulk_save( _design_docs )
        
    def doc_exist(self, docid):
        """Test if document exist in database

        :param docid: str, document id
        :return: boolean, True if document exist
        """

        try:
            data = self.res.head(self.escape_docid(docid))
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
        docid = self.escape_docid(docid)
        if rev is not None:
            doc = self.res.get(docid, rev=rev)
        else:
            doc = self.res.get(docid)

        if wrapper is not None:
            if not callable(wrapper):
                raise TypeError("wrapper isn't a callable")
            return wrapper(doc)
        
        return doc

    def all_docs(self, by_seq=False, **params):
        """Get all documents from database

        This method has the same behavior than view.

        `all_docs( **params )` is the same as `view('_all_docs', **params)`
         and `all_docs( by_seq=True, **params)` is the same as
        `view('_all_docs_by_seq', **params)`

        You can use all(), one(), first() just like views

        Args:
        :param by_seq: bool, if True the "_all_docs_by_seq" is passed to
        couchdb. It will return all updated list.

        :return: list, results of the view
        """
        if by_seq:
            return self.view('_all_docs_by_seq', **params)
        return self.view('_all_docs', **params)
        
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
        docid = self.escape_docid(docid)
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
            docid = self.escape_docid(doc['_id'])
            res = self.res.put(docid, payload=doc)
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
                if nextid:
                    doc['_id'] = nextid
                    
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
                
            docid = self.escape_docid(doc['_id'])
            result = self.res.delete(docid, rev=doc['_rev'])
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
        elif view_name == '_all_docs_by_seq':
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
            content_type=None, content_length=None, chunked=True):
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
        
        content = content or ''
        if content and chunked:
            headers.setdefault("Transfer-Encoding", "chunked")

        if name is None:
            if hasattr(content, "name"):
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

        docid = self.escape_docid(doc_['_id'])
        name = url_quote(name, safe="")
            
        res = self.res(docid).put(name, payload=content, 
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
        docid = self.escape_docid(doc['_id'])
        name = url_quote(name, safe="")
        
        return self.res(docid).delete(name, rev=doc['_rev'])

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
      
        docid = self.escape_docid(docid)
        name = url_quote(name, safe="")
        try:
            data = self.res(docid).get(name)
        except ResourceNotFound:
            return None
        return data
        
    def __len__(self):
        return self.info()['doc_count'] 
        
    def __contains__(self, docid):
        return self.doc_exist(docid)
        
    def __getitem__(self, docid):
        return self.get(docid)
        
    def __setitem__(self, docid, doc):
        doc['_id'] = docid
        self.save_doc(doc)
        
        
    def __delitem__(self, docid):
       self.delete_doc(docid)

    def __iter__(self):
        return self.iterdocuments()
        
    def __nonzero__(self):
        return (len(self) > 0)
        
    def escape_docid(self, docid):
        if docid.startswith('/'):
            docid = docid[1:]
        if docid.startswith('_design'):
            docid = '_design/%s' % url_quote(docid[8:], safe='')
        else:
            docid = url_quote(docid, safe='')
        return docid  

    def encode_attachments(self, attachments):
        for k, v in attachments.iteritems():
            if v.get('stub', False):
                continue
            else:
                re_sp = re.compile('\s')
                v['data'] = re_sp.sub('', base64.b64encode(v['data']))
        return attachments
        
class ViewResults(object):
    """
    Object to retrieve view results.
    """

    def __init__(self, view, **params):
        """
        Constructor of ViewResults object
        
        :attr view: Object inherited from :mod:`couchdbkit.client.view.ViewInterface
        :attr params: params to apply when fetching view.
        
        """
        self.view = view
        self.params = params
        self._result_cache = None
        self._total_rows = None
        self._offset = 0

    def iterator(self):
        self._fetch_if_needed()
        rows = self._result_cache.get('rows', [])
        wrapper = self.view._wrapper
        for row in rows:
            if  wrapper is not None:
                yield self.view._wrapper(row)
            else:
                yield row
                    
    def first(self):
        """
        Return the first result of this query or None if the result doesn’t contain any row.

        This results in an execution of the underlying query.
        """
        
        try:
            return list(self)[0]
        except IndexError:
            return None
    
    def one(self, except_all=False):
        """
        Return exactly one result or raise an exception.
        
        
        Raises `couchdbkit.exceptions.MultipleResultsFound` if multiple rows are returned.
        If except_all is True, raises `couchdbkit.exceptions.NoResultFound` 
        if the query selects no rows. 

        This results in an execution of the underlying query.
        """
        
        length = len(self)
        if length > 1:
            raise MultipleResultsFound("%s results found." % length)

        result = self.first()
        if result is None and except_all:
            raise NoResultFound
        return result

    def all(self):
        """ return list of all results """
        return list(self)

    def count(self):
        """ return number of returned results """
        self._fetch_if_needed()
        return len(self._result_cache.get('rows', []))

    def fetch(self):
        """ fetch results and cache them """
        self._result_cache = self.view._exec(**self.params)
        self._total_rows = self._result_cache.get('total_rows')
        self._offset = self._result_cache.get('offset', 0)

    def _fetch_if_needed(self):
        if not self._result_cache:
            self.fetch()

    @property
    def total_rows(self):
        """ return number of total rows in the view """
        if self._total_rows is None:
            return self.count()
        return self._total_rows

    @property
    def offset(self):
        """ current position in the view """
        self._fetch_if_needed() 
        return self._offset
        
    def __getitem__(self, key):
        params = self.params.copy()
        if type(key) is slice:
            if key.start is not None:
                params['startkey'] = key.start
            if key.stop is not None:
                params['endkey'] = key.stop
        elif isinstance(key, (list, tuple,)):
            params['keys'] = key
        else:
            params['key'] = key
        
        return ViewResults(self.view, params)
        
    def __iter__(self):
        return self.iterator()

    def __len__(self):
        return self.count()

    def __nonzero__(self):
        return bool(len(self))
        
        
class ViewInterface(object):
    
    def __init__(self, db, wrapper=None):
        self._db = db
        self._wrapper = wrapper
        
    def __call__(self, **params):
        return ViewResults(self, **params)
        
    def __iter__(self):
        return self()
        
    def _exec(self, **params):
        raise NotImplementedError
        
class View(ViewInterface):
    
    def __init__(self, db, view_path, wrapper=None):
        ViewInterface.__init__(self, db, wrapper=wrapper)
        self.view_path = view_path
        
        
    def _exec(self, **params):
        if 'keys' in params:
            keys = params.pop('keys')
            return self._db.res.post(self.view_path, payload={ 'keys': keys }, **params)
        else:
            return self._db.res.get(self.view_path, **params)
            

class TempView(ViewInterface):
    def __init__(self, db, design, wrapper=None):
        ViewInterface.__init__(self, db, wrapper=wrapper)
        self.design = design
        self._wrapper = wrapper

    def _exec(self, **params):
        return self._db.res.post('_temp_view', payload=self.design,
                **params)
