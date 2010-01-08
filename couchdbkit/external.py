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

import anyjson
import sys
        
class External(object):
    """ simple class to handle an external
    ans send the response.
    
    example:
    
        from couchdbkit.external import External
        import anyjson

        class Test(External):

            def handle_line(self, line):
                self.send_response(200, 
                    "got message external object %s" % anyjson.serialize(line),
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
            yield anyjson.deserialize(line)
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
        self.write(anyjson.serialize(resp))