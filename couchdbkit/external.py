# -*- coding: utf-8 -
#
# This file is part of couchdbkit released under the MIT license. 
# See the NOTICE for more information.

import sys

from .utils import json

class External(object):
    """ simple class to handle an external
    ans send the response.
    
    example:
    
        from couchdbkit.external import External
        from couchdbkit.utils import json 

        class Test(External):

            def handle_line(self, line):
                self.send_response(200, 
                    "got message external object %s" % json.dumps(line),
                    {"Content-type": "text/plain"})

        if __name__ == "__main__":
            Test().run()
        
    """

    def __init__(self, stdin=sys.stdin, stdout=sys.stdout):
        self.stdin = stdin
        self.stdout = stdout
        
    def handle_line(self, line):
        raise NotImplementedError
        
    def write(self, line):
        self.stdout.write("%s\n" % line)
        self.stdout.flush()
        
    def lines(self):
        line = self.stdin.readline()
        while line:
            yield json.loads(line)
            line = self.stdin.readline()
    
    def run(self):
        for line in self.lines():
            self.handle_line(line)
            
    def send_response(self, code=200, body="", headers={}):
        resp = {
            'code': code, 
            'body': body, 
            'headers': headers
        }
        self.write(json.dumps(resp))
