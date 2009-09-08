from twisted.web import xmlrpc
from twisted.application import service

from fizzjik.interfaces import IRemote, implements
from fizzjik.config import ConfigurableService, if_config

class Namespace(object):
    def __init__(self, method, root):
        self.method = method
        self.root = root

    def __getattr__(self, attr):
        return Namespace(self.method + "." + attr, self.root)

    def __call__(self, *args):
        print "METHOD", self.method, "ARGS", args
        return self.root.callRemote(self.method, *args)

class XMLRPCProxy(xmlrpc.Proxy):
    def __getattr__(self, attr):
        return Namespace(attr, self)

class XMLRPCService(ConfigurableService):
    implements(IRemote)
    endpoint = ""
    enabled = True

    #def __init__(self):
    #    self.proxy = XMLRPCProxy(self.endpoint)
    
    @if_config('enabled')
    def startService(self):
        ConfigurableService.startService(self)
        self.proxy = XMLRPCProxy(self.endpoint)

    def __getattr__(self, attr):
        if self.running:
            return getattr(self.proxy, attr)
        else:
            raise AttributeError
