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
#
# code heavily inspired from django.forms.models
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#    
#    2. Redistributions in binary form must reproduce the above copyright 
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Django nor the names of its contributors may be used
#       to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

""" Implement DocumentForm object. It map Document objects to Form and 
works like ModelForm object :

    >>> from couchdbkit.ext.django.forms  import DocumentForm

    # Create the form class.
    >>> class ArticleForm(DocumentForm):
    ...     class Meta:
    ...         model = Article

    # Creating a form to add an article.
    >>> form = ArticleForm()

    # Creating a form to change an existing article.
    >>> article = Article.get(someid)
    >>> form = ArticleForm(instance=article)
    

The generated Form class will have a form field for every model field. 
Each document property has a corresponding default form field:

* StringProperty   ->  CharField,
* IntegerProperty  ->  IntegerField,
* DecimalProperty  ->  DecimalField,
* BooleanProperty  ->  BooleanField,
* FloatProperty    ->  FloatField,
* DateTimeProperty ->  DateTimeField,
* DateProperty     ->  DateField,
* TimeProperty     ->  TimeField


More fields types will be supported soon.
"""


from django.utils.text import capfirst
from django.utils.datastructures import SortedDict
from django.forms.util import ErrorList
from django.forms.forms import BaseForm, get_declared_fields
from django.forms import fields as f
from django.forms.widgets import media_property

FIELDS_PROPERTES_MAPPING = {
    "StringProperty": f.CharField,
    "IntegerProperty": f.IntegerField,
    "DecimalProperty": f.DecimalField,
    "BooleanProperty": f.BooleanField,
    "FloatProperty": f.FloatField,
    "DateTimeProperty": f.DateTimeField,
    "DateProperty": f.DateField,
    "TimeProperty": f.TimeField
}

def document_to_dict(instance, properties=None, exclude=None):
    """
    Returns a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``properties`` is an optional list of properties names. If provided, 
    only the named properties will be included in the returned dict.

    ``exclude`` is an optional list of properties names. If provided, the named
    properties will be excluded from the returned dict, even if they are listed 
    in the ``properties`` argument.
    """
    # avoid a circular import
    data = {}
    for prop_name in instance._doc.keys():
        if properties and not prop_name in properties:
            continue
        if exclude and prop_name in exclude:
            continue
        data[prop_name] = instance[prop_name]
    return data

def fields_for_document(document, properties=None, exclude=None):
    """
    Returns a ``SortedDict`` containing form fields for the given document.

    ``properties`` is an optional list of properties names. If provided, 
    only the named properties will be included in the returned properties.

    ``exclude`` is an optional list of properties names. If provided, the named
    properties will be excluded from the returned properties, even if 
    they are listed in the ``properties`` argument.
    """
    field_list = []
    
    values = []
    if properties:
        values = [document._properties[prop] for prop in properties if \
                                                prop in document._properties]
    else:
        values = document._properties.values()
        values.sort(lambda a, b: cmp(a.creation_counter, b.creation_counter))
    
    for prop in values: 
        if properties and not prop.name in properties:
            continue
        if exclude and prop.name in exclude:
            continue
        property_class_name = prop.__class__.__name__
        if property_class_name in FIELDS_PROPERTES_MAPPING:
            defaults = {
                'required': prop.required, 
                'label': capfirst(prop.verbose_name), 
            }
            
            if prop.default is not None:
                defaults['initial'] = prop.default_value
                
            if prop.choices:
                if prop.default:
                    defaults['choices'] = prop.default_value() + list(
                                    prop.choices)
                    defaults['coerce'] = prop.to_python
                
            field_list.append((prop.name, 
                FIELDS_PROPERTES_MAPPING[property_class_name](**defaults)))
    return SortedDict(field_list)

class DocumentFormOptions(object):
    def __init__(self, options=None):
        self.document = getattr(options, 'document', None)
        self.properties = getattr(options, 'properties', None)
        self.exclude = getattr(options, 'exclude', None)

class DocumentFormMetaClass(type):
    def __new__(cls, name, bases, attrs):
        try:
            parents = [b for b in bases if issubclass(b, DocumentForm)]
        except NameError:
            # We are defining ModelForm itself.
            parents = None
            
        declared_fields = get_declared_fields(bases, attrs, False)
        new_class = super(DocumentFormMetaClass, cls).__new__(cls, name, bases,
                    attrs)
                
        if not parents:
            return new_class
        
        if 'media' not in attrs:
            new_class.media = media_property(new_class)
    
        opts = new_class._meta = DocumentFormOptions(getattr(new_class, 
                                                'Meta', None))
        
        if opts.document:
            # If a document is defined, extract form fields from it.
            fields = fields_for_document(opts.document, opts.properties,
                                         opts.exclude)
            # Override default docuemnt fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
    
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class
    
class BaseDocumentForm(BaseForm):
    """ Base Document Form object """
    
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, 
            initial=None, error_class=ErrorList, label_suffix=":",
            empty_permitted=False, instance=None):
            
        opts = self._meta
        
        if instance is None:
            self.instance = opts.document()
            object_data = {}
        else:
            self.instance = instance
            object_data = document_to_dict(instance, opts.properties, 
                                        opts.exclude) 
    
        if initial is not None:
            object_data.update(initial)
            
        super(BaseDocumentForm, self).__init__(data, files, auto_id, prefix, 
                                            object_data, error_class, 
                                            label_suffix, empty_permitted)
                                            
    def save(self, commit=True, dynamic=True):
        """
        Saves this ``form``'s cleaned_data into document instance
        ``self.instance``.

        If commit=True, then the changes to ``instance`` will be saved to the
        database. Returns ``instance``.
        """
        
        opts = self._meta
        cleaned_data = self.cleaned_data.copy()
        for prop_name in self.instance._doc.keys():
            if opts.properties and prop_name not in opts.properties:
                continue
            if opts.exclude and prop_name in opts.exclude:
                continue
            if prop_name in cleaned_data:
                value = cleaned_data.pop(prop_name)
                if value is not None:
                    setattr(self.instance, prop_name, value)
            
        if dynamic:
            for attr_name in cleaned_data.keys():
                if opts.exclude and attr_name in opts.exclude:
                    continue
                value = cleaned_data[attr_name]
                if value is not None:
                    setattr(self.instance, attr_name, value)
    
        if commit:
            self.instance.save()
        
        return self.instance
            
class DocumentForm(BaseDocumentForm):
    """ The document form object """
    __metaclass__ = DocumentFormMetaClass          
