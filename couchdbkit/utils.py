# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.


"""
Mostly utility functions couchdbkit uses internally that don't
really belong anywhere else in the modules.
"""
from __future__ import with_statement

import codecs
import string
from hashlib import md5
import os
import re
import sys
import urllib


try:
    import simplejson as json
except ImportError:
    try:
        import json 
    except ImportError:
        raise ImportError("""simplejson isn't installed

Install it with the command:

    pip install simplejson
""")
 

# backport relpath from python2.6
if not hasattr(os.path, 'relpath'):
    if os.name == "nt":
        def splitunc(p):
            if p[1:2] == ':':
                return '', p # Drive letter present
            firstTwo = p[0:2]
            if firstTwo == '//' or firstTwo == '\\\\':
                # is a UNC path:
                # vvvvvvvvvvvvvvvvvvvv equivalent to drive letter
                # \\machine\mountpoint\directories...
                #           directory ^^^^^^^^^^^^^^^
                normp = os.path.normcase(p)
                index = normp.find('\\', 2)
                if index == -1:
                    ##raise RuntimeError, 'illegal UNC path: "' + p + '"'
                    return ("", p)
                index = normp.find('\\', index + 1)
                if index == -1:
                    index = len(p)
                return p[:index], p[index:]
            return '', p
            
        def relpath(path, start=os.path.curdir):
            """Return a relative version of a path"""

            if not path:
                raise ValueError("no path specified")
            start_list = os.path.abspath(start).split(os.path.sep)
            path_list = os.path.abspath(path).split(os.path.sep)
            if start_list[0].lower() != path_list[0].lower():
                unc_path, rest = splitunc(path)
                unc_start, rest = splitunc(start)
                if bool(unc_path) ^ bool(unc_start):
                    raise ValueError("Cannot mix UNC and non-UNC paths (%s and %s)"
                                                                        % (path, start))
                else:
                    raise ValueError("path is on drive %s, start on drive %s"
                                                        % (path_list[0], start_list[0]))
            # Work out how much of the filepath is shared by start and path.
            for i in range(min(len(start_list), len(path_list))):
                if start_list[i].lower() != path_list[i].lower():
                    break
            else:
                i += 1

            rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
            if not rel_list:
                return os.path.curdir
            return os.path.join(*rel_list)
    else:
        def relpath(path, start=os.path.curdir):
            """Return a relative version of a path"""

            if not path:
                raise ValueError("no path specified")

            start_list = os.path.abspath(start).split(os.path.sep)
            path_list = os.path.abspath(path).split(os.path.sep)

            # Work out how much of the filepath is shared by start and path.
            i = len(os.path.commonprefix([start_list, path_list]))

            rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
            if not rel_list:
                return os.path.curdir
            return os.path.join(*rel_list)
else:
    relpath = os.path.relpath

def split_path(path):
    parts = []
    while True:
        head, tail = os.path.split(path)
        parts = [tail] + parts
        path = head
        if not path: break
    return parts

VALID_DB_NAME = re.compile(r'^[a-z][a-z0-9_$()+-/]*$')
SPECIAL_DBS = ("_users", "_replicator",)
def validate_dbname(name):
    """ validate dbname """
    if name in SPECIAL_DBS:
        return True
    elif not VALID_DB_NAME.match(urllib.unquote(name)):
        raise ValueError("Invalid db name: '%s'" % name)
    return True

def to_bytestring(s):
    """ convert to bytestring an unicode """
    if not isinstance(s, basestring):
        return s
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return s
    
def read_file(fname, utf8=True, force_read=False):
    """ read file content"""
    if utf8:
        try:
            with codecs.open(fname, 'rb', "utf-8") as f:
                data = f.read()
                return data
        except UnicodeError:
            if force_read:
                return read_file(fname, utf8=False)
            raise
    else:
        with open(fname, 'rb') as f:
            data = f.read()
            return data

def sign_file(file_path):
    """ return md5 hash from file content
    
    :attr file_path: string, path of file
    
    :return: string, md5 hexdigest
    """
    if os.path.isfile(file_path):
        content = read_file(file_path, force_read=True)
        return md5(to_bytestring(content)).hexdigest()
    return ''

def write_content(fname, content):
    """ write content in a file
    
    :attr fname: string,filename
    :attr content: string
    """
    f = open(fname, 'wb')
    f.write(to_bytestring(content))
    f.close()

def write_json(filename, content):
    """ serialize content in json and save it
    
    :attr filename: string
    :attr content: string
    
    """
    write_content(filename, json.dumps(content))

def read_json(filename, use_environment=False):
    """ read a json file and deserialize
    
    :attr filename: string
    :attr use_environment: boolean, default is False. If
    True, replace environment variable by their value in file
    content
    
    :return: dict or list
    """
    try:
        data = read_file(filename, force_read=True)
    except IOError, e:
        if e[0] == 2:
            return {}
        raise

    if use_environment:
        data = string.Template(data).substitute(os.environ)

    try:
        data = json.loads(data)
    except ValueError:
        print >>sys.stderr, "Json is invalid, can't load %s" % filename
        raise
    return data


