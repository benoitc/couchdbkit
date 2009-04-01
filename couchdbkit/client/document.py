# -*- coding: utf-8 -*-
# Copyright (C) 2007-2008 Christopher Lenz
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


class Document(dict):

    def __init__(self, d=None, db=None):
        self._db = db or None
        dict.__init__(self, d or {})

    def get_id(self):
        return self.get('_id', None)

    def set_id(self, docid):
        if not isinstance(docid, basestring):
            raise TypeError('doc id should be a string')
        self['_id'] = docid
    id = property(get_id, set_id)

    @property
    def rev(self):
        return self.get('_rev')

    def set_database(self, db):
        self._db = db

    def get_database(self):
        if not hasattr(self, '_db'):
            return None
        return self._db
    database = property(get_database, set_database)
 
    new_document = property(lambda self: self.get('_rev') is None) 
    
    def save(self):
        if not hasattr(self, '_db'):
            raise TypeError("doc database required to save document")
        self._db.save(self)

    def put_attachment(self, content, name=None,
        content_type=None, content_length=None):
        """ Add attachement to a document.
 
        :param content: string or :obj:`File` object.
        :param name: name or attachment (file name).
        :param content_type: string, mimetype of attachment.
        If you don't set it, it will be autodetected.
        :param content_lenght: int, size of attachment.

        :return: bool, True if everything was ok.
        """
        if not hasattr(self, '_db'):
            raise TypeError("doc database required to save document")
        return self._db.put_attachment(self, content, name=name,
            content_type=content_type, content_length=content_length)

    def delete_attachment(self, name):
        """ delete attachement of documen
        
        :param name: name of attachement
    
        :return: dict, withm member ok setto True if delete was ok.
        """
        if not hasattr(self, '_db'):
            raise TypeError("doc database required to save document")
        return self._db.delete_attachment(self, name)

    def fetch_attachment(self, name):
        """ get attachment in document
        
        :param name: name of attachment default: default result

        :return: str or unicode, attachment
        """
        if not hasattr(self, '_db'):
            raise TypeError("doc database required to save document")
        return self._db.fetch_attachment(self, name)


    def has_changed(self):
        if self.new_document:
            return True
        else:
            if not hasattr(self, '_db'):
                raise TypeError("doc database required.")
            data = self._db.res.head(self.id)
            resp = self._db.res.get_response()
            if self.rev != resp['etag'].strip('"'):
                return True
        return False
