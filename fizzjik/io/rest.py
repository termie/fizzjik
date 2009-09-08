import inspect
import logging

from twisted.web2 import server, channel
from twisted.web2 import iweb, http, resource, stream
from twisted.internet import defer

import simplejson

from fizzjik.config import ConfigurableTCPServer


"""
wrapper for any other service that probides a RESTish interface
to the methods of that service
"""

class ResterizerWebResource(resource.Resource):
  addSlash = False

  def __init__(self, parent, service, method=None):
    self.parent = parent
    self.service = service
    self.method = method
  
  def childFactory(self, request, segment):
    try:
      f = getattr(self.service, 'getServiceNamed', None)
      if f:
        svc = f(segment)

        return self.__class__(self, svc)
      m = getattr(self.service, segment, None)
      if m:
        svc = self.service
        return self.__class__(self, svc, m)
    except KeyError:
      pass
    except AttributeError:
      pass
    return None
  
  def child_(self, request):
    return self

  def render(self, ctx):
    if self.method:
      return self.renderMethod(ctx)
    elif hasattr(self.service, 'getServiceNamed'):
      return self.renderHub(ctx)
    elif self.service:
      return self.renderService(ctx)
  
  def renderHub(self, ctx):
    services = {}
    for k, s in self.service.namedServices.iteritems():
      services[k] = self._getPublicMethods(s)
    out_methods = self._getPublicMethods(self.service)

    resp = {'service': self.service.name,
            'sub_services': services,
            'public_methods': out_methods}

    return http.Response(stream=simplejson.dumps(resp, sort_keys=True,
                                                 indent=2))

  def renderService(self, ctx):
    out_methods = self._getPublicMethods(self.service)

    resp = {'service': self.service.name,
            'public_methods': out_methods}

    return http.Response(stream=simplejson.dumps(resp, sort_keys=True,
                                                 indent=2))

  def renderMethod(self, ctx):
    req = iweb.IRequest(ctx)
    params = {}
    for k, v in req.args.iteritems():
      params[k] = v[0]
    
    s = stream.ProducerStream()
    f = self.method
    logging.debug('renderMethod: %s' % self.method.func_name)
    d = defer.maybeDeferred(f, **params)
    
    d.addCallback(simplejson.dumps, indent=2)
    d.addCallback(s.write)
    d.addErrback(lambda x: s.write(str(x)))
    d.addBoth(s.finish)

    return http.Response(stream=s)

  def _getPublicMethods(self, svc):
    public_methods = {}

    for k in dir(svc):
      a = getattr(svc, k)
      if hasattr(a, 'public'):
        public_methods[k] = a

    out_methods = {}
    for k, f in public_methods.iteritems():
      out_methods[k] = {}
      out_methods[k]['spec'] = inspect.formatargspec(
          inspect.getargspec(f.im_func))
      out_methods[k]['doc'] = getattr(f, '__doc__', '')
    return out_methods

class ResterizerFactory(channel.HTTPFactory):
  def __init__(self, parent):
    self.parent = parent
    channel.HTTPFactory.__init__(self, self.parent.site)

class ResterizerService(ConfigurableTCPServer):
  rootFactory = ResterizerWebResource
  factory = ResterizerFactory

  def __init__(self, service, *args, **kw):
    self.service = service
    self.root = self.rootFactory(self, service)
    self.site = server.Site(self.root)
    
    super(ResterizerService, self).__init__(*args, **kw)

