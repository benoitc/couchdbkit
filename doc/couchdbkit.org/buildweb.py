#!/usr/bin/env python
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

from __future__ import with_statement

import codecs
import datetime
import os
import re
from stat import *
import sys

from jinja2 import Environment
from jinja2.loaders import FileSystemLoader
from jinja2.utils import open_if_exists
try:
    import markdown
except ImportError:
    markdown = None
    
try:
    from textile import textile
except ImportError:
    textile = None
    
import PyRSS2Gen

import conf


# could be better
re_date = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])-(.*)$')


template_env = Environment(loader=FileSystemLoader(conf.TEMPLATES_PATH, encoding="utf-8"))
template_env.charset = 'utf-8'

def render_template(template_name, _stream=False, **kwargs):
    """ render jinja template """
    tmpl = template_env.get_template(template_name)
    context = kwargs
    if _stream:
        return tmpl.stream(context)
    return tmpl.render(context)
    
def relative_url(value):
    site_url = conf.SITE_URL
    if site_url.endswith('/'):
        site_url = site_url[:-1]
    return value.split(site_url)[1]
template_env.filters['rel_url'] = relative_url
    
def source_newer(source, target):
    if len(sys.argv) > 1 and sys.argv[1] == "force":
        return True

    if not os.path.exists(target): 
        return True
    else:
        smtime = os.stat(source)[ST_MTIME]
        tmtime = os.stat(target)[ST_MTIME]
        return smtime > tmtime

   
def convert_markdown(value):
    md = markdown.Markdown(output_format="html")
    md.set_output_format('html')
    return md.convert(value)
    
def convert_textile(value):
    return textile(value, validate=False, head_offset=False,
            sanitize=False, encoding='utf-8', output='utf-8').decode('utf-8')
            
def rfc3339_date(date):
    # iso8601
    if date.tzinfo:
        return date.strftime('%Y-%m-%dT%H:%M:%S%z')
    else:
        return date.strftime('%Y-%m-%dT%H:%M:%SZ')

    
class Site(object):    
    def __init__(self):
        self.sitemap = []
        self.feed = []
        site_url = conf.SITE_URL
        if site_url.endswith('/'):
            site_url = site_url[:-1]
        self.site_url = site_url

    def process_directory(self, current_dir, files, target_path):
        files = [f for f in files if os.path.splitext(f)[1] in conf.EXTENSIONS]
        blog = None
        for f in files:
            print "process %s" % f
            page = Page(self, f, current_dir, target_path)
            if page.is_blog() and f == "index.txt" or f == "archives.txt":
                continue
            elif page.is_blog():
                if blog is None:
                    blog = Blog(self, current_dir, target_path)
                blog.append(page)
                continue
                
            if not source_newer(page.finput, page.foutput) and f != "index.txt":
                continue
                
            print "write %s" % page.foutput
            try:
                f = codecs.open(page.foutput, 'w', 'utf-8')
                try:
                    f.write(page.render())
                finally:
                    f.close()
            except (IOError, OSError), err:
                raise
            self.sitemap.append(page)
        if blog is not None:
            blog.render()    
        
    def generate_rss(self):
        rss = PyRSS2Gen.RSS2(
            title = conf.SITE_NAME,
            link = conf.SITE_URL,
            description = conf.SITE_DESCRIPTION,
            lastBuildDate = datetime.datetime.utcnow(),
            items = [])
        for i, e in enumerate(self.feed):
            item = PyRSS2Gen.RSSItem(
                    title = e['title'],
                    link = e['link'],
                    description = e['description'],
                    guid = PyRSS2Gen.Guid(e['link']),
                    pubDate = datetime.datetime.fromtimestamp(e['pubDate']))
            rss.items.append(item)
            if i == 15: break
        rss.write_xml(open(os.path.join(conf.OUTPUT_PATH, "feed.xml"), "w"))
        
    def generate_sitemap(self):
        xml = u'<?xml version="1.0" encoding="UTF-8"?>'
        xml += u'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        for page in self.sitemap:
            xml += u'<url>'
            xml += u'<loc>%s</loc>' % page.url
            xml += u'<lastmod>%s</lastmod>' % rfc3339_date(page.headers['published'])
            xml += u'<changefreq>daily</changefreq>'
            xml += u'<priority>0.5</priority>'
            xml += u'</url>'
        xml += u'</urlset>'
        with codecs.open(os.path.join(conf.OUTPUT_PATH, "sitemaps.xml"), "w", "utf-8") as f:
            f.write(xml)
            
            
    def render(self):
        for root, dirs, files in os.walk(conf.INPUT_PATH):
            target_path = root.replace(conf.INPUT_PATH, conf.OUTPUT_PATH)
            if not os.path.isdir(target_path):
                os.makedirs(target_path)
            self.process_directory(root, files, target_path)
            
        if self.feed:
            self.feed.sort(lambda a, b: a['pubDate'] - b['pubDate'], reverse=True)
            self.generate_rss()
        
        if self.sitemap:
            self.generate_sitemap()        

class Blog(object):
    
    def __init__(self, site, current_dir, target_path):
        self.site = site
        self.current_dir = current_dir
        self.target_path = target_path
        self.pages = []
        
    def append(self, page):
        paras = [p for p in page.body.split("\n\n") if p]
        if paras:
            description = "\n\n".join(paras[0:2])
            content_type = page.headers.get('content_type', conf.CONTENT_TYPE)
            if content_type == "markdown":
                description = convert_markdown(description)
            elif content_type == "textile":
                description = convert_textile(description)
        
        m = re_date.match(os.path.splitext(page.filename)[0])
        if m:
            date = "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))
        else:
            date = ""
        page.headers['date'] = date
        
        page.headers['description'] = description
        self.pages.append(page)
        
    def render(self):
        index_page = Page(self.site, "index.txt", self.current_dir, 
            self.target_path)
            
        try:
            archives_page = Page(self.site, "archives.txt", self.current_dir, 
                self.target_path)
        except IOError:
            archives_page = None
            
        if not os.path.isfile(index_page.finput):
            raise IOError, "index.txt isn't found in %s" % self.current_dir
        
            
        self.pages.sort(lambda a, b: a.headers['pubDate'] - b.headers['pubDate'], reverse=True)
        entries = []
        # first pass
        for page in self.pages:
            entry =  {
                "title": page.headers.get('title', page.filename),
                "description":  page.headers['description'],
                "link": page.url,
                "pubDate": page.headers['pubDate'],
                "date": page.headers['date']
            }
            self.site.feed.append(entry)
            entries.append(entry)
            
        self.pages.append(index_page)
        
        if archives_page is not None:
            self.pages.append(archives_page)
        
        # second pass : render pages
        for page in self.pages:
            page.headers['entries'] = entries
            try:
                f = codecs.open(page.foutput, 'w', 'utf-8')
                try:
                    f.write(page.render())
                finally:
                    f.close()
            except (IOError, OSError), err:
                raise
            self.site.sitemap.append(page)

class Page(object):
    content_types = {
        'html': 'text/html',
        'markdown': 'text/html',
        'textile': 'text/html',
        'text': 'text/plain'
    }
    
    files_ext = {
        'html': 'html',
        'markdown': 'html',
        'textile': 'html',
        'text': 'txt'
    }
    
    def __init__(self, site, filename, current_dir, target_path):
        self.filename = filename
        self.current_dir = current_dir
        self.target_path = target_path
        self.finput = os.path.join(current_dir, filename)
        self.parsed = False
        self.foutput = ''
        self.site = site
        self.headers = {}
        self.body = ""
        self.parse()
   
    def get_url(self):
        rel_path = self.foutput.split(conf.OUTPUT_PATH)[1]
        if rel_path.startswith('/'):
            rel_path = rel_path[1:]    
        return "/".join([self.site.site_url, rel_path])
        
    def parse(self):
        with open(self.finput, 'r') as f:
            headers = {}
            raw = f.read()
            try:
                (header_lines,body) = raw.split("\n\n", 1)
                for header in header_lines.split("\n"):
                    (name, value) = header.split(": ", 1)
                    headers[name.lower()] = unicode(value.strip())
                self.headers = headers
                self.headers['pubDate'] = os.stat(self.finput)[ST_CTIME]
                self.headers['published'] = datetime.datetime.fromtimestamp(self.headers['pubDate'])
                self.body = body
                content_type = self.headers.get('content_type', conf.CONTENT_TYPE)
                if content_type in self.content_types.keys(): 
                    self.foutput = os.path.join(self.target_path, 
                            "%s.%s" % (os.path.splitext(self.filename)[0], self.files_ext[content_type]))
                    self.url = self.get_url()
                else:
                    raise TypeError, "Unknown content_type" 
            except:
                raise TypeError, "Invalid page file format for %s" % self.finput
            self.parsed = True
                
    def is_blog(self):
        if not 'page_type' in self.headers:
            return False
        return (self.headers['page_type'] == "blog")

    def render(self):
        if not self.parsed:
            self.parse()
        template = self.headers.get('template', conf.DEFAULT_TEMPLATE)
        content_type = self.headers.get('content_type', conf.CONTENT_TYPE)
        if content_type in self.content_types.keys():
            fun = getattr(self, "render_%s" % content_type)
            return fun(template)
        else:
            raise TypeError, "Unknown content_type" 

    def _render_html(self, template, body):
        kwargs = {
            "body": body,
            "sitename": conf.SITE_NAME,
            "siteurl": conf.SITE_URL,
            "url": self.url
        }
        kwargs.update(self.headers)
        return render_template(template, **kwargs)
        
    def render_html(self, template):
        return self._render_html(template, self.body)
        
    def render_markdown(self, template):
        if markdown is None:
            raise TypeError, "markdown isn't suported"
        body = convert_markdown(self.body)
        return self._render_html(template, body)
        
    def render_textile(self, template):
        if textile is None:
            raise TypeError, "textile isn't suported"
        body = convert_textile(self.body)
        return self._render_html(template, body)
        
    def render_text(self, template):
        return self.body
    
def main():
    site = Site()
    site.render()
    
if __name__ == "__main__":
    main()
