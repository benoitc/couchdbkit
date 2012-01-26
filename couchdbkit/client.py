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

UNKOWN_INFO = {}


from collections import deque
from itertools import groupby
from mimetypes import guess_type
import time

from restkit.util import url_quote

from .exceptions import InvalidAttachment, NoResultFound, \
ResourceNotFound, ResourceConflict, BulkSaveError, MultipleResultsFound
from . import resource
from .utils import validate_dbname


DEFAULT_UUID_BATCH_COUNT = 1000

def _maybe_serialize(doc):
    if hasattr(doc, "to_json"):
        # try to validate doc first
        try:
            doc.validate()
        except AttributeError:
            pass

        return doc.to_json(), True
    elif isinstance(doc, dict):
        return doc.copy(), False

    return doc, False

class Server(object):
    """ Server object that allows you to access and manage a couchdb node.
    A Server object can be used like any `dict` object.
    """

    resource_class = resource.CouchdbResource

    def __init__(self, uri='http://127.0.0.1:5984',
            uuid_batch_count=DEFAULT_UUID_BATCH_COUNT,
            resource_class=None, resource_instance=None,
            **client_opts):

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

        if resource_class is not None:
            self.resource_class = resource_class

        if resource_instance and isinstance(resource_instance,
                                resource.CouchdbResource):
            resource_instance.initial['uri'] = uri
            self.res = resource_instance.clone()
            if client_opts:
                self.res.client_opts.update(client_opts)
        else:
            self.res = self.resource_class(uri, **client_opts)
        self._uuids = deque()

    def info(self):
        """ info of server

        @return: dict

        """
        try:
            resp = self.res.get()
        except Exception:
            return UNKOWN_INFO

        return resp.json_body

    def all_dbs(self):
        """ get list of databases in CouchDb host

        """
        return self.res.get('/_all_dbs').json_body

    def get_db(self, dbname, **params):
        """
        Try to return a Database object for dbname.

        """
        return Database(self._db_uri(dbname), server=self, **params)

    def create_db(self, dbname, **params):
        """ Create a database on CouchDb host

        @param dname: str, name of db
        @param param: custom parameters to pass to create a db. For
        example if you use couchdbkit to access to cloudant or bigcouch:

            Ex: q=12 or n=4

        See https://github.com/cloudant/bigcouch for more info.

        @return: Database instance if it's ok or dict message
        """
        return self.get_db(dbname, create=True, **params)

    get_or_create_db = create_db
    get_or_create_db.__doc__ = """
        Try to return a Database object for dbname. If
        database doest't exist, it will be created.

        """

    def delete_db(self, dbname):
        """
        Delete database
        """
        del self[dbname]

    #TODO: maintain list of replications
    def replicate(self, source, target, **params):
        """
        simple handler for replication

        @param source: str, URI or dbname of the source
        @param target: str, URI or dbname of the target
        @param params: replication options

        More info about replication here :
        http://wiki.apache.org/couchdb/Replication

        """
        payload = {
            "source": source,
            "target": target,
        }
        payload.update(params)
        resp = self.res.post('/_replicate', payload=payload)
        return resp.json_body

    def active_tasks(self):
        """ return active tasks """
        resp = self.res.get('/_active_tasks')
        return resp.json_body

    def uuids(self, count=1):
        return self.res.get('/_uuids', count=count).json_body

    def next_uuid(self, count=None):
        """
        return an available uuid from couchdbkit
        """
        if count is not None:
            self._uuid_batch_count = count
        else:
            self._uuid_batch_count = self.uuid_batch_count

        try:
            return self._uuids.pop()
        except IndexError:
            self._uuids.extend(self.uuids(count=self._uuid_batch_count)["uuids"])
            return self._uuids.pop()

    def __getitem__(self, dbname):
        return Database(self._db_uri(dbname), server=self)

    def __delitem__(self, dbname):
        ret = self.res.delete('/%s/' % url_quote(dbname,
            safe=":")).json_body
        return ret

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

        dbname = url_quote(dbname, safe=":")
        return "/".join([self.uri, dbname])

class Database(object):
    """ Object that abstract access to a CouchDB database
    A Database object can act as a Dict object.
    """

    def __init__(self, uri, create=False, server=None, **params):
        """Constructor for Database

        @param uri: str, Database uri
        @param create: boolean, False by default,
        if True try to create the database.
        @param server: Server instance

        """
        self.uri = uri
        self.server_uri, self.dbname = uri.rsplit("/", 1)

        if server is not None:
            if not hasattr(server, 'next_uuid'):
                raise TypeError('%s is not a couchdbkit.Server instance' %
                            server.__class__.__name__)
            self.server = server
        else:
            self.server = server = Server(self.server_uri, **params)

        validate_dbname(self.dbname)
        if create:
            try:
                self.server.res.head('/%s/' % self.dbname)
            except ResourceNotFound:
                self.server.res.put('/%s/' % self.dbname, **params).json_body

        self.res = server.res(self.dbname)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.dbname)

    def info(self):
        """
        Get database information

        @return: dict
        """
        return self.res.get().json_body


    def compact(self, dname=None):
        """ compact database
        @param dname: string, name of design doc. Usefull to
        compact a view.
        """
        path = "/_compact"
        if dname is not None:
            path = "%s/%s" % (path, resource.escape_docid(dname))
        res = self.res.post(path, headers={"Content-Type":
            "application/json"})
        return res.json_body

    def view_cleanup(self):
        res = self.res.post('/_view_cleanup', headers={"Content-Type":
            "application/json"})
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
        except ResourceNotFound:
            return False
        return True

    def open_doc(self, docid, **params):
        """Get document from database

        Args:
        @param docid: str, document id to retrieve
        @param wrapper: callable. function that takes dict as a param.
        Used to wrap an object.
        @param **params: See doc api for parameters to use:
        http://wiki.apache.org/couchdb/HTTP_Document_API

        @return: dict, representation of CouchDB document as
         a dict.
        """
        wrapper = None
        if "wrapper" in params:
            wrapper = params.pop("wrapper")
        elif "schema" in params:
            schema = params.pop("schema")
            if not hasattr(schema, "wrap"):
                raise TypeError("invalid schema")
            wrapper = schema.wrap

        docid = resource.escape_docid(docid)
        doc = self.res.get(docid, **params).json_body
        if wrapper is not None:
            if not callable(wrapper):
                raise TypeError("wrapper isn't a callable")

            return wrapper(doc)

        return doc
    get = open_doc

    def list(self, list_name, view_name, **params):
        """ Execute a list function on the server and return the response.
        If the response is json it will be deserialized, otherwise the string
        will be returned.

        Args:
            @param list_name: should be 'designname/listname'
            @param view_name: name of the view to run through the list document
            @param params: params of the list
        """
        list_name = list_name.split('/')
        dname = list_name.pop(0)
        vname = '/'.join(list_name)
        list_path = '_design/%s/_list/%s/%s' % (dname, vname, view_name)

        return self.res.get(list_path, **params).json_body

    def show(self, show_name, doc_id, **params):
        """ Execute a show function on the server and return the response.
        If the response is json it will be deserialized, otherwise the string
        will be returned.

        Args:
            @param show_name: should be 'designname/showname'
            @param doc_id: id of the document to pass into the show document
            @param params: params of the show
        """
        show_name = show_name.split('/')
        dname = show_name.pop(0)
        vname = '/'.join(show_name)
        show_path = '_design/%s/_show/%s/%s' % (dname, vname, doc_id)

        return self.res.get(show_path, **params).json_body

    def all_docs(self, by_seq=False, **params):
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
                return self.view('_all_docs_by_seq', **params)
            except ResourceNotFound:
                # CouchDB 0.11 or sup
                raise AttributeError("_all_docs_by_seq isn't supported on Couchdb %s" % self.server.info()[1])

        return self.view('_all_docs', **params)

    def get_rev(self, docid):
        """ Get last revision from docid (the '_rev' member)
        @param docid: str, undecoded document id.

        @return rev: str, the last revision of document.
        """
        response = self.res.head(resource.escape_docid(docid))
        return response['etag'].strip('"')

    def save_doc(self, doc, encode_attachments=True, force_update=False,
            **params):
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
        @param params, list of optionnal params, like batch="ok"

        @return res: result of save. doc is updated in the mean time
        """
        if doc is None:
            doc1 = {}
        else:
            doc1, schema = _maybe_serialize(doc)

        if '_attachments' in doc1 and encode_attachments:
            doc1['_attachments'] = resource.encode_attachments(doc['_attachments'])

        if '_id' in doc:
            docid = doc1['_id']
            docid1 = resource.escape_docid(doc1['_id'])
            try:
                res = self.res.put(docid1, payload=doc1,
                        **params).json_body
            except ResourceConflict:
                if force_update:
                    doc1['_rev'] = self.get_rev(docid)
                    res =self.res.put(docid1, payload=doc1,
                            **params).json_body
                else:
                    raise
        else:
            try:
                doc['_id'] = self.server.next_uuid()
                res =  self.res.put(doc['_id'], payload=doc1,
                        **params).json_body
            except:
                res = self.res.post(payload=doc1, **params).json_body

        if 'batch' in params and 'id' in res:
            doc1.update({ '_id': res['id']})
        else:
            doc1.update({'_id': res['id'], '_rev': res['rev']})


        if schema:
            doc._doc = doc1
        else:
            doc.update(doc1)
        return res

    def save_docs(self, docs, use_uuids=True, all_or_nothing=False,
            **params):
        """ bulk save. Modify Multiple Documents With a Single Request

        @param docs: list of docs
        @param use_uuids: add _id in doc who don't have it already set.
        @param all_or_nothing: In the case of a power failure, when the database
        restarts either all the changes will have been saved or none of them.
        However, it does not do conflict checking, so the documents will

        .. seealso:: `HTTP Bulk Document API <http://wiki.apache.org/couchdb/HTTP_Bulk_Document_API>`

        """

        docs1 = []
        docs_schema = []
        for doc in docs:
            doc1, schema = _maybe_serialize(doc)
            docs1.append(doc1)
            docs_schema.append(schema)

        def is_id(doc):
            return '_id' in doc

        if use_uuids:
            noids = []
            for k, g in groupby(docs1, is_id):
                if not k:
                    noids = list(g)

            uuid_count = max(len(noids), self.server.uuid_batch_count)
            for doc in noids:
                nextid = self.server.next_uuid(count=uuid_count)
                if nextid:
                    doc['_id'] = nextid

        payload = { "docs": docs1 }
        if all_or_nothing:
            payload["all_or_nothing"] = True

        # update docs
        results = self.res.post('/_bulk_docs',
                payload=payload, **params).json_body

        errors = []
        for i, res in enumerate(results):
            if 'error' in res:
                errors.append(res)
            else:
                if docs_schema[i]:
                    docs[i]._doc.update({
                        '_id': res['id'],
                        '_rev': res['rev']
                    })
                else:
                    docs[i].update({
                        '_id': res['id'],
                        '_rev': res['rev']
                    })
        if errors:
            raise BulkSaveError(errors, results)
        return results
    bulk_save = save_docs

    def delete_docs(self, docs, all_or_nothing=False,
            empty_on_delete=False, **params):
        """ bulk delete.
        It adds '_deleted' member to doc then uses bulk_save to save them.

        @param empty_on_delete: default is False if you want to make
        sure the doc is emptied and will not be stored as is in Apache
        CouchDB.
        @param all_or_nothing: In the case of a power failure, when the database
        restarts either all the changes will have been saved or none of them.
        However, it does not do conflict checking, so the documents will

        .. seealso:: `HTTP Bulk Document API <http://wiki.apache.org/couchdb/HTTP_Bulk_Document_API>`


        """

        if empty_on_delete:
            for doc in docs:
                new_doc = {"_id": doc["_id"],
                        "_rev": doc["_rev"],
                        "_deleted": True}
                doc.clear()
                doc.update(new_doc)
        else:
            for doc in docs:
                doc['_deleted'] = True

        return self.bulk_save(docs, use_uuids=False,
                all_or_nothing=all_or_nothing, **params)

    bulk_delete = delete_docs

    def delete_doc(self, doc, **params):
        """ delete a document or a list of documents
        @param doc: str or dict,  document id or full doc.
        @return: dict like:

        .. code-block:: python

            {"ok":true,"rev":"2839830636"}
        """
        result = { 'ok': False }

        doc1, schema = _maybe_serialize(doc)
        if isinstance(doc1, dict):
            if not '_id' or not '_rev' in doc1:
                raise KeyError('_id and _rev are required to delete a doc')

            docid = resource.escape_docid(doc1['_id'])
            result = self.res.delete(docid, rev=doc1['_rev'], **params).json_body
        elif isinstance(doc1, basestring): # we get a docid
            rev = self.get_rev(doc1)
            docid = resource.escape_docid(doc1)
            result = self.res.delete(docid, rev=rev, **params).json_body

        if schema:
            doc._doc.update({
                "_rev": result['rev'],
                "_deleted": True
            })
        elif isinstance(doc, dict):
            doc.update({
                "_rev": result['rev'],
                "_deleted": True
            })
        return result

    def copy_doc(self, doc, dest=None, headers=None):
        """ copy an existing document to a new id. If dest is None, a new uuid will be requested
        @param doc: dict or string, document or document id
        @param dest: basestring or dict. if _rev is specified in dict it will override the doc
        """

        if not headers:
            headers = {}

        doc1, schema = _maybe_serialize(doc)
        if isinstance(doc1, basestring):
            docid = doc1
        else:
            if not '_id' in doc1:
                raise KeyError('_id is required to copy a doc')
            docid = doc1['_id']

        if dest is None:
            destination = self.server.next_uuid(count=1)
        elif isinstance(dest, basestring):
            if dest in self:
                dest = self.get(dest)
                destination = "%s?rev=%s" % (dest['_id'], dest['_rev'])
            else:
                destination = dest
        elif isinstance(dest, dict):
            if '_id' in dest and '_rev' in dest and dest['_id'] in self:
                destination = "%s?rev=%s" % (dest['_id'], dest['_rev'])
            else:
                raise KeyError("dest doesn't exist or this not a document ('_id' or '_rev' missig).")

        if destination:
            headers.update({"Destination": str(destination)})
            result = self.res.copy('/%s' % docid, headers=headers).json_body
            return result

        return { 'ok': False }


    def view(self, view_name, schema=None, wrapper=None, **params):
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
        @param schema, Object with a wrapper function
        @param wrapper: function used to wrap results
        @param params: params of the view

        """
        def get_multi_wrapper(classes, wrap_doc=True,
                dynamic_properties=True):
            def wrapper(row):
                data = row.get('value')
                docid = row.get('id')
                doc = row.get('doc')
                if doc is not None and wrap_doc:
                    try:
                        cls = classes[doc.get('doc_type')]
                        cls._allow_dynamic_properties = dynamic_properties
                        return cls.wrap(doc)
                    except KeyError:
                        return row
                elif not data or data is None:
                    return row
                elif not isinstance(data, dict) or not docid:
                    return row
                else:
                    try:
                        cls = classes[data.get('doc_type')]
                        data['_id'] = docid
                        if 'rev' in data:
                            data['_rev'] = data.pop('rev')
                        cls._allow_dynamic_properties = dynamic_properties
                        return cls.wrap(data)
                    except KeyError:
                        return row

            return wrapper

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

        if schema is not None:
            wrap_doc = params.get('wrap_doc', True)
            dynamic_properties = params.get('dynamic_properties', True)

            if hasattr(schema, "wrap"):
                if hasattr(schema, '_doc_type'):
                    schema = {schema._doc_type: schema}
                    wrapper = get_multi_wrapper(schema, wrap_doc=wrap_doc,
                            dynamic_properties=dynamic_properties)
                else:
                    wrapper = schema.wrap
            else:
                if isinstance(schema, list):
                    schema = dict([(s._doc_type, s) for s in schema])

                wrapper = get_multi_wrapper(schema, wrap_doc=wrap_doc,
                    dynamic_properties=dynamic_properties)

        return View(self, view_path, wrapper=wrapper)(**params)

    def temp_view(self, design, schema=None, wrapper=None, **params):
        """ get adhoc view results. Like view it reeturn a ViewResult object."""
        if schema is not None:
            if not hasattr(schema, 'wrap'):
                raise AttributeError("no 'wrap' method found in obj %s)" % str(schema))
            wrapper = schema.wrap
        return TempView(self, design, wrapper=wrapper)(**params)

    def search( self, view_name, handler='_fti/_design', wrapper=None, **params):
        """ Search. Return results from search. Use couchdb-lucene
        with its default settings by default."""
        return View(self, "/%s/%s" % (handler, view_name), wrapper=wrapper)(**params)

    def documents(self, schema=None, wrapper=None, **params):
        """ return a ViewResults objects containing all documents.
        This is a shorthand to view function.
        """
        return View(self, '_all_docs', schema=schema,
                wrapper=wrapper)(**params)
    iterdocuments = documents

    def put_attachment(self, doc, content, name=None, content_type=None,
            content_length=None, headers=None):
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

        if not headers:
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

        doc1, schema = _maybe_serialize(doc)

        docid = resource.escape_docid(doc1['_id'])
        res = self.res(docid).put(name, payload=content,
                headers=headers, rev=doc1['_rev']).json_body

        if res['ok']:
            new_doc = self.get(doc1['_id'], rev=res['rev'])
            doc.update(new_doc)
        return res['ok']

    def delete_attachment(self, doc, name, headers=None):
        """ delete attachement to the document

        @param doc: dict, document object in python
        @param name: name of attachement

        @return: dict, with member ok set to True if delete was ok.
        """
        doc1, schema = _maybe_serialize(doc)

        docid = resource.escape_docid(doc1['_id'])
        name = url_quote(name, safe="")

        res = self.res(docid).delete(name, rev=doc1['_rev'],
                headers=headers).json_body
        if res['ok']:
            new_doc = self.get(doc1['_id'], rev=res['rev'])
            doc.update(new_doc)
        return res['ok']


    def fetch_attachment(self, id_or_doc, name, stream=False,
            headers=None):
        """ get attachment in a document

        @param id_or_doc: str or dict, doc id or document dict
        @param name: name of attachment default: default result
        @param stream: boolean, if True return a file object
        @return: `restkit.httpc.Response` object
        """

        if isinstance(id_or_doc, basestring):
            docid = id_or_doc
        else:
            doc, schema = _maybe_serialize(id_or_doc)
            docid = doc['_id']

        docid = resource.escape_docid(docid)
        name = url_quote(name, safe="")

        resp = self.res(docid).get(name, headers=headers)
        if stream:
            return resp.body_stream()
        return resp.body_string(charset="utf-8")


    def ensure_full_commit(self):
        """ commit all docs in memory """
        return self.res.post('_ensure_full_commit', headers={
            "Content-Type": "application/json"
        }).json_body

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
            headers={"Content-Type": "application/json"}, **params)
