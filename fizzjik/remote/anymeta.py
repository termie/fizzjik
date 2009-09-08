from fizzjik.config import ConfigurableService, if_config
from fizzjik.remote import rest

class Namespace(object):
    def __init__(self, method, root):
        self.method = method
        self.root = root

    def __getattr__(self, attr):
        return Namespace(self.method + "." + attr, self.root)

    def __call__(self, *args, **kw):
        print "METHOD", self.method, "ARGS", args
        return self.root.call(self.method, *args, **kw)

class RESTService(rest.RESTService):
    base_url = ""
    enabled = True

    username = ""
    password = ""

    def call(self, method, request, format="xml", debug=0, **kw):
        request.setdefault("username", self.username)
        request.setdefault("password", self.password)
        request.setdefault("method", method)
        request.setdefault("format", format)
        return rest.RESTService.call(self, "POST", "", request, debug, **kw)

try:
    import simplejson

    class JSONService(rest.JSONService):
        username = ""
        password = ""

        def call(self, method, request, debug=0, **kw):
            request.setdefault("method", method)
            request.setdefault("username", self.username)
            request.setdefault("password", self.password)
            request.setdefault("format", "json")
            return rest.JSONService.call(self, "POST", "", request, debug, **kw)
except ImportError, e:
    pass

