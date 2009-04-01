from wsgiproxy.exactproxy import proxy_exact_request

class CouchDBProxy(object):

    def __call__(self, environ, start_response):
        environ['SERVER_NAME'] = '127.0.0.1'
        environ['SERVER_PORT'] = '5984'
        return proxy_exact_request(environ, start_response)
        
app = CouchDBProxy()

if __name__ == '__main__':
   from paste.httpserver import serve
   serve(app, 'localhost', 5000)
    