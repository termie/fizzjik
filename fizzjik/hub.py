from ConfigParser import SafeConfigParser as ConfigParser
import logging

from twisted.application import service, internet
from twisted.internet import reactor

from fizzjik.interfaces import IInput, IOutput, IController, IObserver
from fizzjik.interfaces import IConfigurable, implements
from fizzjik.event import ServiceStartEvent, ServiceStopEvent
from fizzjik.config import ConfigurableMixin

class Hub(service.MultiService):
    _observers = None
    _inputs = None
    _controllers = None
    config = None


    def __init__(self, config=None, *args, **kw):
        service.MultiService.__init__(self, *args, **kw)
        self._observers = {}
        self._inputs = {}
        self._controllers = {}

        if config is not None:
            self.config = ConfigParser()
            self.config.read(config)

    @property
    def name(self):
      return self.__class__.__name__

    def startService(self, *args, **kw):
        service.MultiService.startService(self, *args, **kw)
        #self.observe(ServiceStartEvent(self.__class__))
    
    def stopService(self, *args, **kw):
        service.MultiService.stopService(self, *args, **kw)
        #self.observe(ServiceStopEvent(self.__class__))

    def observe(self, evt):
        for cls in self._observers.keys():
            if evt.match(cls):
                for observer in self._observers[cls]:
                    observer[0](evt, *observer[1], **observer[2])
    
    def addService(self, svc):
        logging.debug("Adding service '%s'" % svc.name)
        if IConfigurable.implementedBy(svc.__class__):
            self._sendConfiguration(svc)
        service.MultiService.addService(self, svc)
        if IInput.implementedBy(svc.__class__):
            self._addInput(svc)
        if IOutput.implementedBy(svc.__class__):
            self._addOutput(svc)
        if IController.implementedBy(svc.__class__):
            self._addController(svc)
        if IObserver.implementedBy(svc.__class__):
            self._addObserver(svc)

    def addObserver(self, evt, callback, *args, **kw):
        if evt not in self._observers.keys():
            self._observers[evt] = []
        self._observers[evt].append((callback, args, kw))

    def removeObserver(self, evt, callback):
        self._observers[evt].remove(callback)


    def _addInput(self, input):
        pass

    def _addOutput(self, output):
        pass

    def _addController(self, controller):
        IController(controller).registerObservers(self)

    def _addObserver(self, obs):
        obs = IObserver(obs)
        self.addObserver(obs.event, obs)

    def _sendConfiguration(self, configurable):
        if not self.config:
            return
        IConfigurable(configurable).receiveConfig(self.config)



class ConfigurableHub(Hub, ConfigurableMixin):
    def receiveConfig(self, config):
        ConfigurableMixin.receiveConfig(self, config)
        self.config = config
        for svc in self.services:
            if IConfigurable.implementedBy(svc.__class__):
                self._sendConfiguration(svc)
