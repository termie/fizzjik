import os

from fizzjik.interfaces import IController, implements
from fizzjik.process import ProcessService, ProcessProtocol
from fizzjik.input.network import NetworkConnectionNotPresentEvent, \
        NetworkConnectionPresentEvent, NetworkConnectionRemovedEvent

class DHClientProcessProtocol(ProcessProtocol):
    posix_exec = 'dhclient'
    posix_args = ['dhclient', '-e']

    #def print_(self, f, *args):
    #    self.spawn(*args)
    #    data = f.read()
    #    self.transport.write(data)
    #    self.transport.closeStdin()

class DHClientController(ProcessService):
    implements(IController)
    enabled = True
    platform = "posix"
    protocol = DHClientProcessProtocol

    def registerObservers(self, hub):
        hub.addObserver(NetworkConnectionNotPresentEvent, self._retry)
        hub.addObserver(NetworkConnectionRemovedEvent, self._dhcplease)


    def _retry(self, evt):
        print "trying new network connection"
        self.spawn()

    def _dhcplease(self, evt):
        print "trying new network connection dhcplease"
        self.spawn()
