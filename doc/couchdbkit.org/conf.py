# -*- coding: utf-8 -*-
import os, platform

# options
SITE_NAME = "Couchdbkit"
SITE_URL = "http://www.couchdbkit.org"
SITE_DESCRIPTION = "CouchdDB python framework"


EXTENSIONS = ['.txt', '.md', '.markdown']
DEFAULT_TEMPLATE = "default.html"
CONTENT_TYPE = "textile"


# paths 
DOC_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(DOC_PATH, "templates")
INPUT_PATH = os.path.join(DOC_PATH, "site")
OUTPUT_PATH = os.path.join(DOC_PATH, "htdocs")