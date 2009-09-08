"""
A module for controlling the Denon AVR-3805 Receiver via its serial interface
"""

import re
import logging

from twisted.internet import defer, reactor

from fizzjik.serial import SerialPortClient, SerialPortProtocol
from fizzjik.event import Event
from fizzjik.interfaces import IController, implements
from fizzjik.config import public_method

class AvrEvent(Event):
  pass

class AvrConnectedEvent(Event):
  pass

class AvrDisconnectedEvent(Event):
  pass

class AvrZoneEvent(AvrEvent):
  def __init__(self, zone, data):
    super(AvrZoneEvent, self).__init__(data)
    self.zone = zone
  
  def __repr__(self):
    return "<%s: zone=%s data=%s>" % (self.__class__.__name__, 
                                      self.zone, self.data)

class AvrVolumeEvent(AvrZoneEvent):
  pass

class AvrSourceEvent(AvrZoneEvent):
  pass

class AvrPowerEvent(AvrZoneEvent):
  pass


EVENT_MATCHERS = [
    # Volume Events
    [r'MV(?P<data>\d\d\d?)', AvrVolumeEvent, {'zone': 1}],
    [r'Z1(?P<data>\d\d\d?)', AvrVolumeEvent, {'zone': 3}],
    [r'Z2(?P<data>\d\d\d?)', AvrVolumeEvent, {'zone': 2}],
    
    # Power Events
    [r'ZM(?P<data>ON|OFF)', AvrPowerEvent, {'zone': 1}],
    [r'Z1(?P<data>ON|OFF)', AvrPowerEvent, {'zone': 3}],
    [r'Z2(?P<data>ON|OFF)', AvrPowerEvent, {'zone': 2}],

    # Source Events
    [r'SI(?P<data>[\w\.\-\\]+)', AvrSourceEvent, {'zone': 1}],
    [r'Z1(?P<data>[^O\d][\w\.\-\\]+)', AvrSourceEvent, {'zone': 3}],
    [r'Z2(?P<data>[^O\d][\w\.\-\\]+)', AvrSourceEvent, {'zone': 2}],
    ]

# compile these all plz, kthx
for m in EVENT_MATCHERS:
  m[0] = re.compile(m[0])


class Avr3805(SerialPortClient):
  # implement controller so we can use events to keep our state
  implements(IController)
  
  _canSend = True
  _cmdQueue = None 
  _cmdLock = None

  zones = [1, 2, 3]

  def __init__(self, *args, **kw):
    SerialPortClient.__init__(self, Avr3805Protocol, *args, **kw)
    self.volume = {'1': None, '2': None, '3': None}
    self.source = {'1': None, '2': None, '3': None}
    self.power = {'1': None, '2': None, '3': None}

    self._cmdQueue = []
    self._cmdLock = defer.DeferredLock()
    
  def registerObservers(self, hub):
    hub.addObserver(AvrVolumeEvent, self._onVolumeChange)
    hub.addObserver(AvrSourceEvent, self._onSourceChange)
    hub.addObserver(AvrPowerEvent, self._onPowerChange)
    hub.addObserver(AvrDisconnectedEvent, self._onDisconnect)
    hub.addObserver(AvrConnectedEvent, self._onConnect)
  
  @public_method
  def sendCommand(self, cmd, hold=0.2):
    d = self._cmdLock.acquire()

    def _actuallySendCommand(lock):
      self._connection.protocol.sendCommand(cmd)
      reactor.callLater(hold, lock.release)

    d.addCallback(_actuallySendCommand)
    return d
  
  # High-level commands
  @public_method
  def setVolume(self, zone, volume):
    cmd_prefix = {'1': 'MV', '2': 'Z2', '3': 'Z1'}
    cmd = "%s%s" % (cmd_prefix[str(zone)], str(volume).replace('.', ''))
    self.sendCommand(cmd)

  @public_method
  def setSource(self, zone, source):
    cmd_prefix = {'1': 'SI', '2': 'Z2', '3': 'Z1'}
    cmd = "%s%s" % (cmd_prefix[str(zone)], source.upper())
    self.sendCommand(cmd, hold=2)

  @public_method
  def setPower(self, zone, status):
    cmd_prefix = {'1': 'ZM', '2': 'Z2', '3': 'Z1'}
    cmd = "%s%s" % (cmd_prefix[str(zone)], status.upper())
    self.sendCommand(cmd, hold=2)

  @public_method
  def volumeUp(self, zone):
    cmd_prefix = {'1': 'MV', '2': 'Z2', '3': 'Z1'}
    cmd = "%sUP" % cmd_prefix[str(zone)]
    self.sendCommand(cmd)

  @public_method
  def volumeDown(self, zone):
    cmd_prefix = {'1': 'MV', '2': 'Z2', '3': 'Z1'}
    cmd = "%sDOWN" % cmd_prefix[str(zone)]
    self.sendCommand(cmd)

  @public_method
  def allZones(self, method, **kw):
    out = []
    for zone in self.zones:
      f = getattr(self, method)
      assert f.public
      out.append(f(zone=zone, **kw))
    return out

  # Event handlers
  def _onVolumeChange(self, evt):
    volume = evt.data
    if len(volume) > 2:
      volume = "%s.%s" % (volume[:2], volume[2])
    volume = round(float(volume), 1)

    self.volume[evt.zone] = volume

  def _onSourceChange(self, evt):
    source = evt.data.lower()
    self.source[evt.zone] = source

  def _onPowerChange(self, evt):
    status = {'ON': 1, 'OFF': 0}[evt.data]
    self.power[evt.zone] = status

  def _onConnect(self, evt):
    pass

  def _onDisconnect(self, evt):
    pass

class Avr3805Protocol(SerialPortProtocol):
  baudrate = 9600
  
  def __init__(self, parent):
    self.parent = parent
  
  def dataReceived(self, data):
    evt = None
    for m in EVENT_MATCHERS:
      matched = m[0].match(data)
      if matched:
        params = m[2]
        params.update(matched.groupdict())
        evt = m[1](**params)
        break
    if not evt:
      evt = AvrEvent(data)
    self.parent.observe(evt)
    
  def sendCommand(self, cmd):
    logging.debug('sendCommand %s', cmd)
    bytes = [ord(x) for x in cmd]
    bytes.append(0x0D)
    self.writeBytes(bytes)
