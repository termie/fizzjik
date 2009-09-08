from twisted.internet import defer

from fizzjik.serial import SerialPortClient, SerialPortProtocol
from fizzjik.rfid import TagAddedEvent, TagPresentEvent, TagRemovedEvent
from fizzjik.event import InputAddedEvent, InputPresentEvent, InputRemovedEvent
from fizzjik.config import if_config

class MifareInputPresentEvent(InputPresentEvent):
    def __init__(self, data, port1, port2):
        self.port1 = port1
        self.port2 = port2
        super(MifareInputPresentEvent, self).__init__(data)

class MifareInputAddedEvent(InputAddedEvent):
    def __init__(self, data, port1, port2):
        self.port1 = port1
        self.port2 = port2
        super(MifareInputAddedEvent, self).__init__(data)

class MifareInputRemovedEvent(InputRemovedEvent):
    def __init__(self, data, port1, port2):
        self.port1 = port1
        self.port2 = port2
        super(MifareInputRemovedEvent, self).__init__(data)

class SonMicroMifareSensor(SerialPortClient):
    def __init__(self, *args, **kw):
        self.outputs = (0, 0)
        SerialPortClient.__init__(self, SonMicroMifareSensorProtocol, *args, **kw)

    @if_config("enabled")
    def startService(self):
        SerialPortClient.startService(self)
        self._startReadLoop()

    @if_config("enabled")
    def stopService(self):
        if self.running:
            self._stopReadLoop()
        SerialPortClient.stopService(self)

    def _startReadLoop(self):
        self._connection.protocol._startReadLoop()
    
    def _stopReadLoop(self):
        self._connection.protocol._stopReadLoop()

class SonMicroMifareSensorProtocol(SerialPortProtocol):
    """only senses one tag at a time"""
    baudrate = 57600
    
    buffer = ""
    last = None
    parent = None

    has_inputs = True
    has_outputs = True

    _deferred = None

    SELECT_TAG      = (0xFF, 0x00, 0x01, 0x83, 0x84)
    READ_INPUT_PORT = (0xFF, 0x00, 0x01, 0x91, 0x92)
    RESET           = (0xFF, 0x00, 0x01, 0x80, 0x81)

    def __init__(self, parent):
        self.parent = parent
        self._currentOutputs = (0, 0)
        self._currentInputs = (0, 0)
        self.timers = {}

    def dataReceived(self, data):
        #print "RECV: ", "BYTES[%s]"%(", ".join(["%X"%(ord(x)) for x in data]))
        self.buffer += data

        try:
            if len(self.buffer) < 4:
                return
            if ord(self.buffer[3]) == 0x83 and ord(self.buffer[2]) > 0x02:
                if len(self.buffer) < 10:
                    return
            if len(self.buffer) < 6:
                return
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.buffer = ""
            return

        
        if self._deferred:
            self._deferred.callback(self.buffer);
        self.buffer = ""
        #print " ".join([ord(x) for x in data]).encode('utf-8')
        #data = re.sub("""\x8c""", "", data)
        #self.buffer += data
        ##print "recv", data, self.buffer
        #m = self.TAG.match(self.buffer)
        #if m:
        #    self.buffer = self.buffer[len(m.group(0)):]
        #    #self.buffer = ""
        #    tag = m.group(1)

        #    if tag == self.last:
        #        self._tagPresent(tag)
        #    else:
        #        if not self.last:
        #            self._tagAdded(tag)
        #        else:
        #            self._tagRemoved(self.last)
        #            self._tagAdded(tag)

    def _startReadLoop(self):
        #self.writeBytes(self.RESET)
        self._doLoop(self)

    def _readTag(self):
        d = defer.Deferred()
        d.addCallback(self._parseReadTagResponse)
        self._deferred = d
        self.writeBytes(self.SELECT_TAG)
        return d

    def _parseReadTagResponse(self, data):
        if ord(data[2]) == 0x02:
            return None
        else:
            tag = "".join(["%02X"%(ord(x)) for x in data[5:9]]) 
            self._tagSensed(tag)
            return None

    def _readInput(self):
        d = defer.Deferred()
        d.addCallback(self._parseReadInputResponse)
        self._deferred = d
        self.writeBytes(self.READ_INPUT_PORT)
        return d

    def _parseReadInputResponse(self, data):
        if ord(data[4]) == 0x00:
            return None
        else:
            raw = ord(data[4])
            ports = [raw & 0x01, raw & 0x02 and 1 or 0]
            self._inputSensed(ports)
            return None

    def _enjoyOutput(self):
        if self.parent.outputs != self._currentOutputs:
            d = defer.Deferred()
            bytes = [0xFF, 0x00, 0x02, 0x92]
            outputByte = 0x00
            if self.parent.outputs[0]:
                outputByte += 0x01
            if self.parent.outputs[1]:
                outputByte += 0x02
            bytes.append(outputByte)
            bytes.append(0x94 + outputByte)
            d.addCallback(self._parseEnjoyOutputResponse)
            self._deferred = d
            self.writeBytes(bytes)
            return d
        else:
            return None

    def _parseEnjoyOutputResponse(self, data):
        outputs = ord(data[4])
        self._currentOutputs = (outputs & 0x01, outputs & 0x02 and 1 or 0)
        return

    def _doLoop(self, foo=None):
        if not self.parent.running:
            return
        

        d = self._readTag()
        if self.has_inputs:
            d.addCallback(lambda _: self._readInput())
        if self.has_outputs:
            d.addCallback(lambda _: self._enjoyOutput())
        d.addCallback(lambda _: self._doLoop())
        def _pr(s):
            print s
        d.addErrback(_pr)
        
        #d = defer.Deferred()
        #d.addCallback(lambda _: self.writeBytes

        ##self.writeBytes(self.SELECT_TAG)
        #self.writeBytes(self.READ_INPUT_PORT)
        #self.transport.reactor.callLater(3, self._doRead)
        

    def _stopReadLoop(self):
        pass
    
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

    def _inputSensed(self, ports):
        if self._currentInputs == ports:
            self._inputPresent(ports)
        else:
            self._inputAdded(ports)
        
    def _inputPresent(self, ports):
        evt = MifareInputPresentEvent(ports, ports[0], ports[1])
        self.bumpTimer(self._inputRemoved, 'input', ports)
        self.parent.observe(evt)
    
    def _inputAdded(self, ports):
        self._currentInputs = ports
        evt = MifareInputAddedEvent(ports, ports[0], ports[1])
        self.bumpTimer(self._inputRemoved, 'input', ports)
        self.parent.observe(evt)

    def _inputRemoved(self, ports):
        self._currentInputs = (0, 0)
        evt = MifareInputRemovedEvent(ports, ports[0], ports[1])
        self.clearTimer('input')
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

