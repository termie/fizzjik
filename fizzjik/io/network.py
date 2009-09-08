from twisted.internet import task, defer
from twisted.web import client

from fizzjik.input.basic import PollingInput
from fizzjik.event import InputAddedEvent, InputPresentEvent, InputRemovedEvent

class NetworkConnectionAddedEvent(InputAddedEvent):
    pass

class NetworkConnectionPresentEvent(InputPresentEvent):
    pass

class NetworkConnectionNotPresentEvent(InputPresentEvent):
    pass

class NetworkConnectionRemovedEvent(InputRemovedEvent):
    pass

class NetworkConnectionSensor(PollingInput):
    destination = "http://term.ie"
    timeout = 10
    
    status = True

    def poll(self):
        self._fetch()

    def _fetch(self):
        d = client.getPage(self.destination, timeout=self.timeout)
        d.addCallbacks(self._fetchSuccess, self._fetchFailure)
        return d

    def _fetchSuccess(self, o):
        if self.status:
            self.observe(NetworkConnectionPresentEvent(True))
        else:
            self.status = True
            self.observe(NetworkConnectionAddedEvent(True))

    def _fetchFailure(self, o):
        if self.status:
            self.status = False
            self.observe(NetworkConnectionRemovedEvent(o))
        else:
            self.observe(NetworkConnectionNotPresentEvent(o))
