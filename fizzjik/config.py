from twisted.application import service
from twisted.application import internet

from fizzjik.interfaces import IConfigurable, implements

# decorator
def if_config(option, f0=None):
    def deco(f):
        def wrapper(self, *args, **kw):
            if not getattr(self, option):
                return
            f(self, *args, **kw)
        return wrapper
    if f0:
        return deco(f0)
    return deco

def public_method(f):
  f.public = True
  return f


class ConfigurableMixin(object):
    implements(IConfigurable)
    
    config = None
    def receiveConfig(self, config):
        section = self.__class__.__name__
        if not config.has_section(section):
            section_mod = getattr(self.__class__, '_instances', 0)
            section = "%s_%s"%(section, section_mod)
            if not config.has_section(section):
                return
            else:
                self.__class__._instances = section_mod + 1
        self.config = config
        for o in config.options(section):
            try:
                if hasattr(self, "_config_%s"%(o)):
                    f = getattr(self, "_config_%s"%(o))
                    f(config.get(section, o))
                elif type(getattr(self, o)) is type(2):
                    setattr(self, o, config.getint(section, o))
                elif type(getattr(self, o)) is type(2.0):
                    setattr(self, o, config.getfloat(section, o))
                elif type(getattr(self, o)) is type(True):
                    setattr(self, o, config.getboolean(section, o))
                else:
                    setattr(self, o, config.get(section, o))
            except AttributeError:
                pass



class ConfigurableService(service.Service, ConfigurableMixin):
    enabled = True

    privilegedStartService = \
            if_config("enabled", service.Service.privilegedStartService)
    startService = if_config("enabled", service.Service.startService)

    @property
    def name(self):
      return self.__class__.__name__

    
class ConfigurableTCPServer(internet.TCPServer, ConfigurableMixin):
    enabled = True
    port = 0 # you'll need to pick a default
    factory = None # your factory here

    def _getPort(self):
        from twisted.internet import reactor
        factoryInst = self.factory(self)
        if IConfigurable.implementedBy(self.factory):
            factoryInst.receiveConfig(self.config)

        return getattr(reactor, 'listen'+self.method)(self.port, factoryInst, *self.args, **self.kwargs)

    privilegedStartService = \
            if_config("enabled", internet.TCPServer.privilegedStartService)
    startService = if_config("enabled", internet.TCPServer.startService)

    @property
    def name(self):
      return self.__class__.__name__
