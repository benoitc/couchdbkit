# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

"""
Macros used by loaders. compatible with couchapp. It allow you to include code,
design docs members inside your views, shows and lists.

for example to include a code, add just after first function the line :
    
    // !code relativepath/to/some/code.js
    
To include a member of design doc and use it as a simple javascript object :

    // !json some.member.i.want.to.include
    
All in one, example of a view :

    function(doc) {
        !code _attachments/js/md5.js
        
        if (doc.type == "user") {
            doc.gravatar = hex_md5(user.email);
            emit(doc.username, doc)
        }
    }

This example includes md5.js code and uses md5 function to create gravatar hash
in your views.  So you could just store raw data in your docs and calculate
hash when views are updated.

"""

import glob
import os
import re
import sys
from hashlib import md5

import anyjson

from couchdbkit.utils import read_file, read_json, to_bytestring

def package_shows(doc, funcs, app_dir, objs, verbose=False):
    """ take a list of funcs un return them processed """
    apply_lib(doc, funcs, app_dir, objs, verbose=verbose)
         
def package_views(doc, views, app_dir, objs, verbose=False):
    """ take a dict of funcs and return them processed """
    
    for view, funcs in views.iteritems():
        try:
            apply_lib(doc, funcs, app_dir, objs, verbose=verbose)
        except AttributeError, e:
            # malformated views
            msg = """View %s is invalid. Folder structure is: 
designpathg/designname/views/viewname/{map,reduce}.js""" % view
            print >>sys.stderr, msg
            sys.exit(-1)
                
        
def apply_lib(doc, funcs, app_dir, objs, verbose=False):
    """ run code macros and json macros on a list of funcs. It also 
    maintain a list of processed code to be sure to not processing twice
    """
    for k, v in funcs.iteritems():
        if isinstance(v, basestring):
            old_v = v
            try:
                funcs[k] = run_json_macros(doc, 
                    run_code_macros(v, app_dir, verbose=verbose), 
                    app_dir, verbose=verbose)
            except ValueError, e:
                print >>sys.stderr, "Error running !code or !json on function \"%s\": %s" % (k, e)
                sys.exit(-1)
            if old_v != funcs[k]:
                objs[md5(to_bytestring(funcs[k])).hexdigest()] = old_v
           

def run_code_macros(f_string, app_dir, verbose=False):
    """ apply code macros"""
    def rreq(mo):
        # just read the file and return it
        path = os.path.join(app_dir, mo.group(2).strip())
        library = ''
        filenum = 0
        for filename in glob.iglob(path):            
            if verbose>=2:
               print "process code macro: %s" % filename
            try:
               library += read_file(filename)
            except IOError, e:
               print >>sys.stderr, e
               sys.exit(-1)
            filenum += 1

        if not filenum:
            print >>sys.stderr, "Processing code: No file matching '%s'" % mo.group(2)
            sys.exit(-1)

        return library

    re_code = re.compile('(\/\/|#)\ ?!code (.*)')
    return re_code.sub(rreq, f_string)

def run_json_macros(doc, f_string, app_dir, verbose=False):
    """ apply json macros """
    included = {}
    varstrings = []

    def rjson(mo):
        if mo.group(2).startswith('_attachments'): 
            # someone  want to include from attachments
           path = os.path.join(app_dir, mo.group(2).strip())
           filenum = 0
           for filename in glob.iglob(path):
               library = ''
               try:
                   if filename.endswith('.json'):
                       library = read_json(filename)
                   else:
                       library = read_file(filename)
               except IOError, e:
                   print >>sys.stderr, e
                   sys.exit(1)
               filenum += 1
               current_file = filename.split(app_dir)[1]
               fields = current_file.split('/')
               count = len(fields)
               include_to = included
               for i, field in enumerate(fields):
                   if i+1 < count:
                       include_to[field] = {}
                       include_to = include_to[field]
                   else:
                       include_to[field] = library
           if not filenum:
               print >>sys.stderr, "Processing code: No file matching '%s'" % mo.group(2)
               sys.exit(-1)
        else:	
            fields = mo.group(2).split('.')
            library = doc
            count = len(fields)
            include_to = included
            for i, field in enumerate(fields):
                if not field in library: break
                library = library[field]
                if i+1 < count:
                    include_to[field] = include_to.get(field, {})
                    include_to = include_to[field]
                else:
                    include_to[field] = library

        return f_string

    def rjson2(mo):
        return '\n'.join(varstrings)

    re_json = re.compile('(\/\/|#)\ ?!json (.*)')
    re_json.sub(rjson, f_string)

    if not included:
        return f_string

    for k, v in included.iteritems():
        varstrings.append("var %s = %s;" % (k, anyjson.serialize(v)))

    return re_json.sub(rjson2, f_string)
