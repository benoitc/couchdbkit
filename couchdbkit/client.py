# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""
Client implementation for CouchDB access. It allows you to manage a CouchDB
server, databases, documents and views. All objects mostly reflect python
objects for convenience. Server and Database objects for example, can be
used as easy as a dict.

Example:

    >>> from couchdbkit import Server
    >>> server = Server()
    >>> db = server.create_db('couchdbkit_test')
    >>> doc = { 'string': 'test', 'number': 4 }
    >>> db.save_doc(doc)
    >>> docid = doc['_id']
    >>> doc2 = db.get(docid)
    >>> doc['string']
    u'test'
    >>> del db[docid]
    >>> docid in db
    False
    >>> del server['simplecouchdb_test']

"""




import base64
import cgi
from itertools import groupby
from mimetypes import guess_type
import re
import time
import urlparse
import warnings

import anyjson
from restkit.util import url_quote

from couchdbkit.exceptions import *
import couchdbkit.resource as resource
from couchdbkit.utils import validate_dbname

DEFAULT_UUID_BATCH_COUNT = 1000

def maybe_raw(response, raw=False):
    if raw:
        return response
    return response.json_body

class Server(object):
    """ Server object that allows you to access and manage a couchdb node.
    A Server object can be used like any `dict` object.
    """

    def __init__(self, uri='http://127.0.0.1:5984',
            uuid_batch_count=DEFAULT_UUID_BATCH_COUNT, resource_instance=None):
        """ constructor for Server object

        @param uri: uri of CouchDb host
        @param uuid_batch_count: max of uuids to get in one time
        @param resource_instance: `restkit.resource.CouchdbDBResource` instance.
            It alows you to set a resource class with custom parameters.
        """

        if not uri or uri is None:
            raise ValueError("Server uri is missing")

        if uri.endswith("/"):
            uri = uri[:-1]

        self.uri = uri
        self.uuid_batch_count = uuid_batch_count
        self._uuid_batch_count = uuid_batch_count

        if resource_instance and isinstance(resource_instance, 
                                resource.CouchdbResource):
            resource_instance.uri = uri
            self.res = resource_instance.clone()
        else:
            self.res = resource.CouchdbResource(uri)
        self._uuids = []

    def info(self, _raw_json=False):
        """ info of server
        @param _raw_json: return raw json instead deserializing it

        @return: dict

        """
        return maybe_raw(self.res.get(), raw=_raw_json)

    def all_dbs(self, _raw_json=False):
        """ get list of databases in CouchDb host

        @param _raw_json: return raw json instead deserializing it
        """
        return maybe_raw(self.res.get('/_all_dbs'), raw=_raw_json)

    def create_db(self, dbname):
        """ Create a database on CouchDb host

        @param dname: str, name of db

        @return: Database instance if it's ok or dict message
        """
        return Database(self._db_uri(dbname), create=True,
                    server=self)

    def get_or_create_db(self, dbname):
        """
        Try to return a Database object for dbname. If
        database doest't exist, it will be created.

        """
        return Database(self._db_uri(dbname), create=True,
                    server=self)

    def delete_db(self, dbname):
        """
        Delete database
        """
        del self[dbname]

    #TODO: maintain list of replications
    def replicate(self, source, target, continuous=False):
        """
        simple handler for replication

        @param source: str, URI or dbname of the source
        @param target: str, URI or dbname of the target
        @param continuous: boolean, default is False, set the type of replication

        More info about replication here :
        http://wiki.apache.org/couchdb/Replication

        """
        res = self.res.post('/_replicate', payload={
            "source": source,
            "target": target,
            "continuous": continuous
        })

    def uuids(self, count=1, raw=False):
        return maybe_raw(self.res.get('/_uuids', count=count))


    def next_uuid(self, count=None):
        """
        return an available uuid from couchdbkit
        """
        if count is not None:
            self._uuid_batch_count = count
        else:
            self._uuid_batch_count = self.uuid_batch_count

        self.uuids = self.uuids or []
        if not self._uuids:
            self._uuids = self.uuids(count=self._uuid_batch_count)["uuids"]
        return self._uuids.pop()

    def add_authorization(self, obj_auth):
        """
        Allow you to add basic authentication or any authentication
        object inherited from `restkit`.

        ex:

            >>> from couchdbkit import Server
            >>> from restkit import BasicAuth
            >>> server = Server()
            >>> server.add_authorization(BasicAuth(username, password))
        """
        self.res.add_filter(obj_auth)

    def __getitem__(self, dbname):
        return Database(self._db_uri(dbname), server=self)

    def __delitem__(self, dbname):
        return self.res.delete('/%s/' % url_quote(dbname, safe=":"))

    def __contains__(self, dbname):
        try:
            self.res.head('/%s/' % url_quote(dbname, safe=":"))
        except:
            return False
        return True

    def __iter__(self):
        for dbname in self.all_dbs():
            yield Database(self._db_uri(dbname), server=self)

    def __len__(self):
        return len(self.all_dbs())

    def __nonzero__(self):
        return (len(self) > 0)

    def _db_uri(self, dbname):
        if dbname.startswith("/"):
            dbname = dbname[1:]
        return "/".join([self.uri, dbname])

class Database(object):
    """ Object that abstract access to a CouchDB database
    A Database object can act as a Dict object.
    """

    def __init__(self, uri, create=False, server=None):
        """Constructor for Database

        @param uri: str, Database uri
        @param create: boolean, False by default,
        if True try to create the database.
        @param server: Server instance

        """
        uri_parsed = urlparse.urlparse(uri)
        self.server_uri = "%s://%s" % (uri_parsed.scheme, uri_parsed.netloc)
        self.dbname = uri_parsed.path.strip("/")

        if server is not None:
            if not hasattr(server, 'next_uuid'):
                raise TypeError('%s is not a couchdbkit.server instance' %
                            server.__class__.__name__)
            self.server = server
        else:
            self.server = server = Server(self.server_uri)

        try:
            self.server.res.head('/%s/' % url_quote(self.dbname, safe=":"))
        except resource.ResourceNotFound:
            if create:
                self.server.res.put('/%s/' % url_quote(self.dbname, safe=":"))
            else:
                raise

        self.res = server.res.clone()
        if "/" in self.dbname:
            self.res.safe = ":/%"
        self.res.update_uri('/%s' % url_quote(self.dbname, safe=":"))

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.dbname)

    @classmethod
    def from_uri(cls, uri, *args, **kwargs):
        """ Create a database from its url. """
        warnings.warn("from_uri is deprecated", DeprecationWarning)
        return cls(uri)

    def info(self, _raw_json=False):
        """
        Get database information

        @param _raw_json: return raw json instead deserializing it

        @return: dict
        """
        return maybe_raw(self.res.get(), raw=_raw_json)


    def compact(self, dname=None):
        """ compact database
        @param dname: string, name of design doc. Usefull to
        compact a view.
        """
        path = "/_compact"
        if dname is not None:
            path = "%s/%s" % (path, resource.escape_docid(dname))
        res = self.res.post(path)
        return res.json_body

    def view_cleanup(self):
        res = self.res.post('/_view_cleanup')
        return res.json_body

    def flush(self):
        """ Remove all docs from a database
        except design docs."""
        # save ddocs
        all_ddocs = self.all_docs(startkey="_design",
                            endkey="_design/"+u"\u9999",
                            include_docs=True)
        ddocs = []
        for ddoc in all_ddocs:
            ddoc['doc'].pop('_rev')
            ddocs.append(ddoc['doc'])

        # delete db
        self.server.delete_db(self.dbname)

        # we let a chance to the system to sync
        time.sleep(0.2)

        # recreate db + ddocs
        self.server.create_db(self.dbname)
        self.bulk_save(ddocs)

    def doc_exist(self, docid):
        """Test if document exists in a database

        @param docid: str, document id
        @return: boolean, True if document exist
        """

        try:
            self.res.head(resource.escape_docid(docid))
        except resource.ResourceNotFound:
            return False
        return True

    def get(self, docid, rev=None, wrapper=None, _raw_json=False):
        """Get document from database

        Args:
        @param docid: str, document id to retrieve
        @param rev: if specified, allows you to retrieve
        a specific revision of document
        @param wrapper: callable. function that takes dict as a param.
        Used to wrap an object.
        @param _raw_json: return raw json instead deserializing it

        @return: dict, representation of CouchDB document as
         a dict.
        """
        docid = resource.escape_docid(docid)
        if rev is not None:
            doc = maybe_raw(self.res.get(docid, rev=rev), raw=_raw_json)
        else:
            doc = maybe_raw(self.res.get(docid), raw=_raw_json)

        if wrapper is not None:
            if not callable(wrapper):
                raise TypeError("wrapper isn't a callable")
            return wrapper(doc)

        return doc

    def all_docs(self, by_seq=False, _raw_json=False, **params):
        """Get all documents from a database

        This method has the same behavior as a view.

        `all_docs( **params )` is the same as `view('_all_docs', **params)`
         and `all_docs( by_seq=True, **params)` is the same as
        `view('_all_docs_by_seq', **params)`

        You can use all(), one(), first() just like views

        Args:
        @param by_seq: bool, if True the "_all_docs_by_seq" is passed to
        couchdb. It will return an updated list of all documents.

        @return: list, results of the view
        """
        if by_seq:
            try:
                return self.view('_all_docs_by_seq', _raw_json=_raw_json, **params)
            except resource.ResourceNotFound:
                # CouchDB 0.11 or sup
                raise AttributeError("_all_docs_by_seq isn't supported on Couchdb %s" % self.server.info()[1])

        return self.view('_all_docs', _raw_json=_raw_json, **params)

    def doc_revisions(self, docid, with_doc=True, _raw_json=False):
        """ retrieve revisions of a doc

        @param docid: str, id of document
        @param with_doc: bool, if True return document
        dict with revisions as member, if false return
        only revisions
        @param _raw_json: return raw json instead deserializing it

        @return: dict: '_rev_infos' member if you have set with_doc
        to True :


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
        docid = resource.escape_docid(docid)
        try:
            if with_doc:
                doc_with_revs = maybe_raw(self.res.get(docid, revs=True),
                                    raw=_raw_json)
            else:
                doc_with_revs = maybe_raw(self.res.get(docid, revs_info=True),
                                    raw=_raw_json)
        except resource.ResourceNotFound:
            return None
        return doc_with_revs

    def get_rev(self, docid):
        """ Get last revision from docid (the '_rev' member)
        @param docid: str, undecoded document id.

        @return rev: str, the last revision of document.
        """
        response = self.res.head(resource.escape_docid(docid))
        return response.headers['etag'].strip('"')

    def save_doc(self, doc, encode_attachments=True, force_update=False,
            _raw_json=False, **params):
        """ Save a document. It will use the `_id` member of the document
        or request a new uuid from CouchDB. IDs are attached to
        documents on the client side because POST has the curious property of
        being automatically retried by proxies in the event of network
        segmentation and lost responses. (Idee from `Couchrest <http://github.com/jchris/couchrest/>`)

        @param doc: dict.  doc is updated
        with doc '_id' and '_rev' properties returned
        by CouchDB server when you save.
        @param force_update: boolean, if there is conlict, try to update
        with latest revision
        @param _raw_json: return raw json instead deserializing it
        @param params, list of optionnal params, like batch="ok"

        with `_raw_json=True` It return raw response. If False it update
        doc instance with new revision (if batch=False).

        @return res: result of save. doc is updated in the mean time
        """
        if doc is None:
            doc = {}

        if '_attachments' in doc and encode_attachments:
            doc['_attachments'] = resource.encode_attachments(doc['_attachments'])

        if '_id' in doc:
            docid = doc['_id']
            docid1 = resource.escape_docid(doc['_id'])
            try:
                res = maybe_raw(self.res.put(docid1, payload=doc,
                            **params), raw=_raw_json)
            except resource.ResourceConflict:
                if force_update:
                    doc['_rev'] = self.get_rev(docid)
                    res = maybe_raw(self.res.put(docid1, payload=doc,
                                **params), raw=_raw_json)
                else:
                    raise
        else:
            try:
                doc['_id'] = self.server.next_uuid()
                res =  maybe_raw(self.res.put(doc['_id'], payload=doc, **params),
                            raw=_raw_json)
            except:
                res = maybe_raw(self.res.post(payload=doc, **params), raw=_raw_json)

        if _raw_json:
            return res

        if 'batch' in params and 'id' in res:
            doc.update({ '_id': res['id']})
        else:
            doc.update({'_id': res['id'], '_rev': res['rev']})

        return res

    def bulk_save(self, docs, use_uuids=True, all_or_nothing=False, _raw_json=False):
        """ bulk save. Modify Multiple Documents With a Single Request

        @param docs: list of docs
        @param use_uuids: add _id in doc who don't have it already set.
        @param all_or_nothing: In the case of a power failure, when the database
        restarts either all the changes will have been saved or none of them.
        However, it does not do conflict checking, so the documents will
        @param _raw_json: return raw json instead deserializing it
        be committed even if this creates conflicts.

        With `_raw_json=True` it return raw response. When False it return anything
        but update list of docs with new revisions and members (like deleted)

        .. seealso:: `HTTP Bulk Document API <http://wiki.apache.org/couchdb/HTTP_Bulk_Document_API>`

        """
        # we definitely need a list here, not any iterable, or groupby will fail
        docs = list(docs)

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
            payload["all_or_nothing"] = True

        # update docs
        results = maybe_raw(self.res.post('/_bulk_docs', payload=payload),
                        raw=_raw_json)

        if _raw_json:
            return results

        errors = []
        for i, res in enumerate(results):
            if 'error' in res:
                errors.append(res)
            else:
                docs[i].update({'_id': res['id'], '_rev': res['rev']})
        if errors:
            raise BulkSaveError(errors)


    def bulk_delete(self, docs, all_or_nothing=False, _raw_json=False):
        """ bulk delete.
        It adds '_deleted' member to doc then uses bulk_save to save them.

        @param _raw_json: return raw json instead deserializing it

        With `_raw_json=True` it return raw response. When False it return anything
        but update list of docs with new revisions and members.

        """
        for doc in docs:
            doc['_deleted'] = True
        self.bulk_save(docs, use_uuids=False, all_or_nothing=all_or_nothing,
                    _raw_json=_raw_json)

    def delete_doc(self, doc, _raw_json=False):
        """ delete a document or a list of documents
        @param doc: str or dict,  document id or full doc.
        @param _raw_json: return raw json instead deserializing it
        @return: dict like:

        .. code-block:: python

            {"ok":true,"rev":"2839830636"}
        """
        result = { 'ok': False }
        if isinstance(doc, dict):
            if not '_id' or not '_rev' in doc:
                raise KeyError('_id and _rev are required to delete a doc')

            docid = resource.escape_docid(doc['_id'])
            result = maybe_raw(self.res.delete(docid, rev=doc['_rev']),
                        raw=_raw_json)
        elif isinstance(doc, basestring): # we get a docid
            rev = self.get_rev(doc)
            docid = resource.escape_docid(doc)
            result = maybe_raw(self.res.delete(docid, rev=rev),
                            raw=_raw_json)
        return result

    def copy_doc(self, doc, dest=None, _raw_json=False):
        """ copy an existing document to a new id. If dest is None, a new uuid will be requested
        @param doc: dict or string, document or document id
        @param dest: basestring or dict. if _rev is specified in dict it will override the doc
        @param _raw_json: return raw json instead deserializing it
        """
        if isinstance(doc, basestring):
            docid = doc
        else:
            if not '_id' in doc:
                raise KeyError('_id is required to copy a doc')
            docid = doc['_id']

        if dest is None:
            destination = self.server.next_uuid(count=1)
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
            result = maybe_raw(self.res.copy('/%s' % docid,
                        headers={ "Destination": str(destination) }),
                        raw=_raw_json)
            return result

        result = { 'ok': False }
        if _raw_json:
            return anyjson.serialize(result)
        return result


    def view(self, view_name, obj=None, wrapper=None, **params):
        """ get view results from database. viewname is generally
        a string like `designname/viewname". It return an ViewResults
        object on which you could iterate, list, ... . You could wrap
        results in wrapper function, a wrapper function take a row
        as argument. Wrapping could be also done by passing an Object
        in obj arguments. This Object should have a `wrap` method
        that work like a simple wrapper function.

        @param view_name, string could be '_all_docs', '_all_docs_by_seq',
        'designname/viewname' if view_name start with a "/" it won't be parsed
        and beginning slash will be removed. Usefull with c-l for example.
        @param obj, Object with a wrapper function
        @param wrapper: function used to wrap results
        @param params: params of the view

        """
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

    def temp_view(self, design, obj=None, wrapper=None, **params):
        """ get adhoc view results. Like view it reeturn a ViewResult object."""
        if obj is not None:
            if not hasattr(obj, 'wrap'):
                raise AttributeError(" no 'wrap' method found in obj %s)" % str(obj))
            wrapper = obj.wrap
        return TempView(self, design, wrapper=wrapper)(**params)

    def search( self, view_name, handler='_fti', wrapper=None, **params):
        """ Search. Return results from search. Use couchdb-lucene
        with its default settings by default."""
        return View(self, "/%s/%s" % (handler, view_name), wrapper=wrapper)(**params)

    def documents(self, wrapper=None, **params):
        """ return a ViewResults objects containing all documents.
        This is a shorthand to view function.
        """
        return View(self, '_all_docs', wrapper=wrapper)(**params)
    iterdocuments = documents

    def put_attachment(self, doc, content, name=None, content_type=None,
            content_length=None):
        """ Add attachement to a document. All attachments are streamed.

        @param doc: dict, document object
        @param content: string or :obj:`File` object.
        @param name: name or attachment (file name).
        @param content_type: string, mimetype of attachment.
        If you don't set it, it will be autodetected.
        @param content_lenght: int, size of attachment.

        @return: bool, True if everything was ok.


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

        if not content:
            content = ""
            content_length = 0
        if name is None:
            if hasattr(content, "name"):
                name = content.name
            else:
                raise InvalidAttachment('You should provide a valid attachment name')
        name = url_quote(name, safe="")
        if content_type is None:
            content_type = ';'.join(filter(None, guess_type(name)))

        if content_type:
            headers['Content-Type'] = content_type

        # add appropriate headers
        if content_length and content_length is not None:
            headers['Content-Length'] = content_length

        if hasattr(doc, 'to_json'):
            doc1 = doc.to_json()
        else:
            doc1 = doc

        docid = resource.escape_docid(doc1['_id'])
        res = self.res(docid).put(name, payload=content,
                headers=headers, rev=doc1['_rev']).json_body

        if res['ok']:
            new_doc = self.get(doc1['_id'], rev=res['rev'])
            doc.update(new_doc)
        return res['ok']

    def delete_attachment(self, doc, name):
        """ delete attachement to the document

        @param doc: dict, document object in python
        @param name: name of attachement

        @return: dict, with member ok set to True if delete was ok.
        """
        docid = resource.escape_docid(doc['_id'])
        name = url_quote(name, safe="")

        res = self.res(docid).delete(name, rev=doc['_rev']).json_body
        if res['ok']:
            new_doc = self.get(doc['_id'], rev=res['rev'])
            doc.update(new_doc)
        return res['ok']


    def fetch_attachment(self, id_or_doc, name, stream=False):
        """ get attachment in a document

        @param id_or_doc: str or dict, doc id or document dict
        @param name: name of attachment default: default result
        @param stream: boolean, if True return a file object
        @return: `restkit.httpc.Response` object
        """

        if isinstance(id_or_doc, basestring):
            docid = id_or_doc
        else:
            docid = id_or_doc['_id']

        docid = resource.escape_docid(docid)
        name = url_quote(name, safe="")

        resp = self.res(docid).get(name)
        if stream:
            return resp.body_file
        return resp.unicode_body


    def ensure_full_commit(self, _raw_json=False):
        """ commit all docs in memory """
        return maybe_raw(self.res.post('_ensure_full_commit'), raw=_raw_json)

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
        return self.documents().iterator()

    def __nonzero__(self):
        return (len(self) > 0)

class ViewResults(object):
    """
    Object to retrieve view results.
    """

    def __init__(self, view, **params):
        """
        Constructor of ViewResults object

        @param view: Object inherited from :mod:`couchdbkit.client.view.ViewInterface
        @param params: params to apply when fetching view.

        """
        self.view = view
        self.params = params
        self._result_cache = None
        self._total_rows = None
        self._offset = 0
        self._dynamic_keys = []

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
        return list(self.iterator())

    def count(self):
        """ return number of returned results """
        self._fetch_if_needed()
        return len(self._result_cache.get('rows', []))

    def fetch(self):
        """ fetch results and cache them """
        # reset dynamic keys
        for key in  self._dynamic_keys:
            try:
                delattr(self, key)
            except:
                pass
        self._dynamic_keys = []

        self._result_cache = self.view._exec(**self.params).json_body
        self._total_rows = self._result_cache.get('total_rows')
        self._offset = self._result_cache.get('offset', 0)

        # add key in view results that could be added by an external
        # like couchdb-lucene
        for key in self._result_cache.keys():
            if key not in ["total_rows", "offset", "rows"]:
                self._dynamic_keys.append(key)
                setattr(self, key, self._result_cache[key])


    def fetch_raw(self):
        """ retrive the raw result """
        return self.view._exec(**self.params)

    def _fetch_if_needed(self):
        if not self._result_cache:
            self.fetch()

    @property
    def total_rows(self):
        """ return number of total rows in the view """
        self._fetch_if_needed()
        # reduce case, count number of lines
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

        return ViewResults(self.view, **params)

    def __iter__(self):
        return self.iterator()

    def __len__(self):
        return self.count()

    def __nonzero__(self):
        return bool(len(self))


class ViewInterface(object):
    """ Generic object interface used by View and TempView objects. """

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
    """ Object used to wrap a view and return ViewResults.
    Generally called via the `view` method in a `Database` instance. """

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
    """ Object used to wrap a temporary and return ViewResults. """
    def __init__(self, db, design, wrapper=None):
        ViewInterface.__init__(self, db, wrapper=wrapper)
        self.design = design
        self._wrapper = wrapper

    def _exec(self, **params):
        return self._db.res.post('_temp_view', payload=self.design,
                **params)
