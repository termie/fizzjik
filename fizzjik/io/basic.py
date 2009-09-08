from twisted.protocols import basic
from twisted.internet import protocol, task
from twisted.application import service

from twisted.application import internet

from fizzjik.interfaces import IInput, implements
from fizzjik.interfaces import IOutput, IController
from fizzjik.event import Event
from fizzjik.config import ConfigurableTCPServer, ConfigurableService, \
        if_config, public_method


class LineReceiverProtocol(basic.LineReceiver):
    delimiter = "\n"
    def lineReceived(self, line):
        self.factory.observe(self.factory.builder(line.strip()))


class LineReceiverFactory(protocol.ServerFactory):
    protocol = LineReceiverProtocol
    def __init__(self, service):
        self.service = service

    @property
    def builder(self):
        return self.service.builder

    def observe(self, evt):
        self.service.observe(evt)


class LineReceiver(ConfigurableTCPServer):
    implements(IInput)

    port = 0
    factory = LineReceiverFactory
    builder = Event

    def observe(self, evt):
        self.parent.observe(evt)

    @public_method
    def receiveLine(self, line):
        self.observe(self.builder(line.strip()))

class Input(ConfigurableService):
    implements(IInput)

    def observe(self, evt):
        self.parent.observe(evt)

class PollingInput(Input):
    delay = 10
    immediate = False

    def __init__(self):
        self.poller = task.LoopingCall(self.poll)

    @if_config('enabled')
    def startService(self):
        Input.startService(self)
        self.poller.start(self.delay, self.immediate)
    
    @if_config('enabled')
    def stopService(self):
        Input.stopService(self)
        self.poller.stop()

    def poll(self):
        self.observe(Event("POLL"))


class Output(ConfigurableService):
    implements(IOutput)
    pass


class Echo(Output):
    implements(IController)

    def registerObservers(self, hub):
        hub.addObserver(Event, self._echo)

    @if_config('enabled')
    def _echo(self, evt):
        print evt
