from twisted.internet import protocol
from twisted.internet.interfaces import IConnector
import twisted.internet.serialport as serialport

from twisted.application.internet import GenericClient

from fizzjik.interfaces import IInput, IConfigurable, implements
from fizzjik.config import ConfigurableMixin, if_config
from fizzjik.event import ServiceStartEvent, ServiceStopEvent, ExceptionEvent


class SerialPortClient(GenericClient, ConfigurableMixin):
    implements(IInput, IConfigurable)
    enabled = True
    device = "/dev/ttyS0"
    proto = None

    def __init__(self, proto, *args, **kw):
        self.proto = proto
        GenericClient.__init__(self, *args, **kw)

    def receiveConfig(self, config):
        ConfigurableMixin.receiveConfig(self, config)
        self.config = config

    def _getConnection(self):
        from twisted.internet import reactor           
        protoInst = self.proto(self)
        if self.config:
            protoInst.receiveConfig(self.config)
            return getattr(reactor, 'connect'+self.method)(SerialPortConnector,
                                                           protoInst,
                                                           self.device,
                                                           *self.args,
                                                           **self.kwargs)
            

    startService = if_config("enabled", GenericClient.startService)

    def connectionLost(self, reason):
        pass

    def observe(self, evt):
        self.parent.observe(evt)

    @property
    def name(self):
      return self.__class__.__name__

class SerialPortProtocol(protocol.Protocol, ConfigurableMixin):
    baudrate = 9600
    bytesize = serialport.EIGHTBITS
    parity = serialport.PARITY_NONE
    stopbits = serialport.STOPBITS_ONE
    timeout = 0
    xonxoff = 0
    rtscts = 0

    def __init__(self, parent):
        self.parent = parent

    def writeBytes(self, bytes):
        self.transport.write("".join([chr(x) for x in bytes]))

    def connectionLost(self, reason):
      protocol.Protocol.connectionLost(self, reason)
      self.parent.connectionLost(reason)

    def connect(self):
      self.transport.connect()

    def disconnect(self):
      self.transport.disconnect()

class SerialPortConnector(serialport.SerialPort):
    implements(IConnector)

    def __init__(self, proto, dev, reactor):
        self.proto = proto
        serialport.SerialPort.__init__(self, proto, dev, reactor,
                                       baudrate=proto.baudrate,
                                       bytesize=proto.bytesize,
                                       parity=proto.parity,
                                       stopbits=proto.stopbits,
                                       timeout=proto.timeout,
                                       xonxoff=proto.xonxoff,
                                       rtscts=proto.rtscts)
        
    def connect(self):
        self._serial.open()
        self.resumeProducing()

    def disconnect(self):
        self.stopProducing()

    def write(self, data):
        if self._serial.isOpen():
          try:
              #print "send", data
              pass
          except UnicodeDecodeError, e:
              #print "send",  "BYTES[%s]"%(", ".join(["%X"%(ord(x)) for x in data]))
              pass
          #print "send",  "BYTES[%s]"%(", ".join(["%X"%(ord(x)) for x in data]))
          self.writeSomeData(data)
        else:
          print "LOST!"

    def connectionLost(self, reason):
      serialport.SerialPort.connectionLost(self, reason)
      self.proto.connectionLost(reason)

