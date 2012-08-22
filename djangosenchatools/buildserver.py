import logging
import threading
from SocketServer import ThreadingMixIn
from django.core.servers.basehttp import WSGIServer
from django.core.servers.basehttp import WSGIRequestHandler
from django.core.servers.basehttp import get_internal_wsgi_application

log = logging.getLogger('senchatoolsbuild')


class BuildServerThread(threading.Thread):
    """
    Thread for running a live http server while the tests are running.
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.is_ready = threading.Event()
        self.error = None
        super(BuildServerThread, self).__init__()

    def run(self):
        """
        Sets up the live server and databases, and then loops over handling
        http requests.
        """
        server_address = (self.host, self.port)
        threading = True
        if threading:
            httpd_cls = type('WSGIServer', (ThreadingMixIn, WSGIServer), {})
        else:
            httpd_cls = WSGIServer
        self.httpd = httpd_cls(server_address, WSGIRequestHandler, ipv6=False)
        wsgi_handler = get_internal_wsgi_application()
        self.httpd.set_app(wsgi_handler)
        self.is_ready.set()
        self.httpd.serve_forever()


    def join(self, timeout=None):
        if hasattr(self, 'httpd'):
            # Stop the WSGI server
            self.httpd.shutdown()
            self.httpd.server_close()
        super(BuildServerThread, self).join(timeout)



def build_with_buildserver(hostname, port, builder):
    server_thread = BuildServerThread(hostname, port)
    server_thread.daemon = True
    server_thread.start()

    # Wait for the live server to be ready
    server_thread.is_ready.wait()
    if server_thread.error:
        raise server_thread.error

    server_url = 'http://{0}:{1}'.format(server_thread.host, server_thread.port)
    log.info('Listening on %s', server_url)

    # Run the builder callable
    builder()
    #raw_input()

    ## Stop the server
    log.info('Stopping buildserver %s ...', server_url)
    server_thread.join()
    log.info('... buildserver stopped')
