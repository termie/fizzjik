import os

from twisted.application import service
from twisted.internet import protocol, reactor

from Growl import GrowlNotifier

from fizzjik.interfaces import IOutput, IConfigurable, implements
from fizzjik.config import ConfigurableMixin, if_config

class GrowlService(service.Service, ConfigurableMixin):
    implements(IOutput)
    
    enabled = True
    platform = "darwin"

    name = "fizzjik"
    notifications = None
    
    def __init__(self):
        self.notifications = ["event"]

    def _config_notifications(self, value):
        self.notifications = value.split(",")

    @if_config('enabled')
    def startService(self):
        service.Service.startService(self)
        self.notifier = GrowlNotifier(self.name, self.notifications)
        self.notifier.register()

    def stopService(self):
        service.Service.stopService(self)
    
    def notify(self, *args, **kw):
        self.notifier.notify(*args, **kw)

    def defaultNotify(self, event):
        self.notify("event", title=event.__class__.__name__, description=event.data)
