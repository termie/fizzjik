import re

from fizzjik.serial import SerialPortClient, SerialPortProtocol
from fizzjik.rfid import TagAddedEvent, TagPresentEvent, TagRemovedEvent

class EasyIdentSensor(SerialPortClient):
    def __init__(self, *args, **kw):
        SerialPortClient.__init__(self, EasyIdentSensorProtocol, *args, **kw)

class EasyIdentSensorProtocol(SerialPortProtocol):
    """only senses one tag at a time"""
    baudrate = 9600
    
    buffer = ""
    last = None
    timer = None
    parent = None

    TAG = re.compile("""\s*(\S{11})\s*""")

    def __init__(self, parent):
        self.parent = parent

    def dataReceived(self, data):
        data = re.sub("""\x8c""", "", data)
        self.buffer += data
        #print "recv", data, self.buffer
        m = self.TAG.match(self.buffer)
        if m:
            self.buffer = self.buffer[len(m.group(0)):]
            #self.buffer = ""
            tag = m.group(1)

            if tag == self.last:
                self._tagPresent(tag)
            else:
                if not self.last:
                    self._tagAdded(tag)
                else:
                    self._tagRemoved(self.last)
                    self._tagAdded(tag)

    def _tagPresent(self, tag):
        evt = TagPresentEvent(tag)
        self.bumpTimer(tag)
        self.parent.observe(evt)

    def _tagAdded(self, tag):
        self.last = tag
        self.bumpTimer(tag)
        evt = TagAddedEvent(tag)
        self.parent.observe(evt)

    def _tagRemoved(self, tag):
        self.clearTimer()
        self.last = None
        evt = TagRemovedEvent(tag)
        self.parent.observe(evt)

    def clearTimer(self):
        if self.timer and not self.timer.called:
            self.timer.cancel()
        self.timer = None

    def bumpTimer(self, tag):
        if self.timer and not self.timer.called:
            self.timer.cancel()
        # XXX andy: okay, this is sort of a hack due to the weirdness that
        #           that is the serialport connector
        self.timer = self.transport.reactor.callLater(0.3, self._tagRemoved, 
                                                      tag)



