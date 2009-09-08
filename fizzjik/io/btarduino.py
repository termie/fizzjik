from twisted.internet import defer
import re
from fizzjik.serial import SerialPortClient, SerialPortProtocol
from fizzjik.rfid import TagAddedEvent, TagPresentEvent, TagRemovedEvent
from fizzjik.config import if_config

class BTArduinoSensor(SerialPortClient):
    def __init__(self, *args, **kw):
        self.outputs = (0, 0)
        SerialPortClient.__init__(self, BTArduinoSensorProtocol, *args, **kw)

class BTArduinoSensorProtocol(SerialPortProtocol):
    """only senses one tag at a time"""
    baudrate = 115200
    
    buffer = ""
    parent = None

    _deferred = None

    TAG_RE = re.compile(r"""\s*(\S{8})\s*""")

    def __init__(self, parent):
        self.parent = parent
        self.timers = {}

    def dataReceived(self, data):
        print "RECV: ", "BYTES[%s]"%(", ".join(["%X"%(ord(x)) for x in data]))
        self.buffer += data

        match = self.TAG_RE.match(self.buffer)
        if match:
            self.buffer = self.buffer[len(match.group(0)):]
            tag = match.group(1)
            self._tagSensed(tag)

    def _tagSensed(self, tag):
        if tag not in self.timers:
            self._tagAdded(tag)
        elif self.timers[tag].called:
            self._tagAdded(tag)
        else:
            self._tagPresent(tag)

    def _tagPresent(self, tag):
        evt = TagPresentEvent(tag)
        self.bumpTimer(self._tagRemoved, tag, tag)
        self.parent.observe(evt)

    def _tagAdded(self, tag):
        self.last = tag
        self.bumpTimer(self._tagRemoved, tag, tag)
        evt = TagAddedEvent(tag)
        self.parent.observe(evt)

    def _tagRemoved(self, tag):
        self.clearTimer(tag)
        self.last = None
        evt = TagRemovedEvent(tag)
        self.parent.observe(evt)

    def clearTimer(self, which):
        if which in self.timers and not self.timers[which].called:
            self.timers[which].cancel()
        del self.timers[which]

    def bumpTimer(self, cb, which, *args):
        if which in self.timers and not self.timers[which].called:
            self.timers[which].cancel()
        # XXX andy: okay, this is sort of a hack due to the weirdness that
        #           that is the serialport connector
        self.timers[which] = self.transport.reactor.callLater(0.3, cb, *args)

