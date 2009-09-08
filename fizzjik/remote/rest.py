import urllib
import pprint

from twisted.web import client
from twisted.application import service

from fizzjik.interfaces import IRemote, implements
from fizzjik.config import ConfigurableService, if_config

class RESTService(ConfigurableService):
    implements(IRemote)
    base_url = ""
    enabled = True

    def call(self, method, url, request, debug=0, **kw):
        if method == "GET":
            query = urllib.urlencode(request)
            url = query_string_append(url, query)
            data = None
        elif method == "POST":
            data = urllib.urlencode(request)
        if self.base_url:
            url = self.base_url + url
        
        params = dict(url=url,
                      method=method,
                      postdata=data)
        params.update(kw)
        params.setdefault("headers", {})
        if method == "POST":
            params['headers'].setdefault('Content-type', 
                                         'application/x-www-form-urlencoded')
        d = client.getPage(**params)
        if debug:
            d.addCallback(lambda x: pprint.pprint(x) and x or x)
        return d

try:
    import simplejson

    class JSONService(RESTService):
        def call(self, method, url, request, debug=0, **kw):
            def _decode(data):
                try:
                    rv = simplejson.loads(data)
                except ValueError, e:
                    pprint.pprint(data)
                    raise
                return rv
            d = RESTService.call(self, method, url, request, debug, **kw)
            d.addCallback(_decode)
            return d
except ImportError, e:
    pass

        
def query_string_append(url, query_string):
    if url.find("?") != -1:
        sep = "&"
    else:
        sep = "?"

    return url + sep + query_string
