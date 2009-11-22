import logging

try:
  import uuid
  generateId = lambda: uuid.uuid4().hex
except ImportError:
  import random
  generateId = lambda: str(random.randint(100000))

import urllib
import StringIO

from twisted.web2 import server, channel, http_headers
from twisted.web2 import iweb, http, resource, stream
from twisted.internet import defer, reactor

import simplejson

from fizzjik.config import ConfigurableTCPServer
from fizzjik import event

"""
listen to and publish events via Cometd

Example javascript (after including dojo):

<script type="text/javascript">
  dojo.require("dojox.cometd");
  dojo.require("dojox.cometd.longPollTransportJsonEncoded");
  dojo.addOnLoad(function () {
    dojox.cometd.init("/cometd");
    
    dojox.cometd.subscribe("/AvrVolumeEvent", function(message) {
      console.log("received", message);
    });
  });
</script>


"""


cometClients = {}
subscriptions = {}

class CometPublishEvent(event.Event):
  def __init__(self, channel, data, clientId=None):
    self.channel = channel
    self.data = data
    self.clientId = clientId


class CometClient(object):
  def __init__(self, stream):
    self.stream = stream
    self.packets = []
    self.open = True

  def setStream(self, stream):
    self.stream = stream
    self.open = True
  
  def writeFirst(self, packet):
    self.packets.insert(0, packet)

  def write(self, packet):
    self.packets.append(packet)

  def finish(self):
    if not self.open:
      return

    self.stream.write(simplejson.dumps(self.packets))
    logging.info('sent %s', self.packets)
    self.stream.finish()
    self.packets = []
    self.open = False

class CometdWebResource(resource.PostableResource):
  addSlash = False

  def __init__(self, parent, service, method=None):
    self.parent = parent
    self.service = service

  def child_cometd(self, request):
    return self
  
  def http_POST(self, request):
    ctype = request.headers.getHeader('content-type')
    if ctype.mediaType == 'text' and ctype.mediaSubtype == 'json':
      out = []
      d = stream.readStream(request.stream, lambda x: out.append(x))
      d.addCallback(lambda _: simplejson.loads(''.join(out)))
      d.addCallback(lambda res: self.render(request, res))
    else:
      d = server.parsePOSTData(
          request, self.maxMem, self.maxFields, self.maxSize)
      d.addCallback(lambda res: self.render(request))
    return d

  def render(self, request, json=None):
    if json is None:
      req = iweb.IRequest(request)
      json = simplejson.loads(req.args.get('message', ['[]'])[0])

    producer = stream.ProducerStream()
    for message in json:
      clientId = message.get('clientId', None)
      if clientId and cometClients[clientId]:
        client = cometClients[clientId]
        client.setStream(producer)
      else:
        client = CometClient(producer)
      self.messageReceived(message['channel'], message, client)

    headers = http_headers.Headers()
    headers.addRawHeader('Content-Type', 'text/json')
    return http.Response(stream=producer, headers=headers)

  def messageReceived(self, channel, message, client):
    logging.info('messageReceived (%s): %s', channel, message)
    if channel == '/meta/handshake':
      self.handleHandshake(message, client)
    elif channel == '/meta/connect':
      self.handleConnect(message, client)
    elif channel == '/meta/subscribe':
      self.handleSubscribe(message, client)

  def handleHandshake(self, message, client):
    clientId = generateId()
    # stub a comet client
    cometClients[clientId] = None
    response = {'channel': '/meta/handshake',
                'supportedConnectionTypes': ['long-polling',
                                             'long-polling-json-encoded'],
                'version': '1.0',
                'clientId': clientId,
                'successful': True
                }
    client.write(response)
    client.finish()
  
  def handleConnect(self, message, client):
    clientId = message['clientId']
    if clientId not in cometClients:
      # error!
      client.finish()
      return
    
    firstConnect = True
    if cometClients[clientId] is not None:
      firstConnect = False

    cometClients[clientId] = client
    response = {'channel': '/meta/connect',
                'successful': True,
                'clientId': clientId,
                }
    client.writeFirst(response)

    # if this is the first time respond right away so they can subscribe
    if firstConnect:
      client.finish()
    
  def handleSubscribe(self, message, client):
    clientId = message['clientId']
    if clientId not in cometClients:
      # error!
      client.finish()
      return
    
    subscription = message['subscription']
    if subscription not in subscriptions:
      subscriptions[subscription] = set()
      logging.info('Adding observer for: %s', subscription[1:])
      self.service.addObserver(subscription[1:], self.dispatch)
    subscriptions[subscription].add(clientId)

    response = {'channel': '/meta/subscribe',
                'clientId': clientId,
                'subscription': subscription,
                'successful': True,
                }
    client.writeFirst(response)
    client.finish()
  
  def handlePublish(self, message, client):
    clientId = message['clientId']
    if clientId not in cometClients:
      # error!
      client.finish()
      return

    channel = message['channel']
    event = CometPublishEvent(channel=channel,
                              data=message['data'],
                              clientId=message['clientId'])
    self.service.observe(event)
    response = {'channel': channel,
                'successful': True,
                }
    client.writeFirst(response)
    client.finish()

  def dispatch(self, evt):
    for cls in subscriptions:
      # ignore the initial slash ("/")
      if evt.match(cls[1:]):
        for subscriber in subscriptions[cls]:
          self.sendEvent(subscriber, cls, evt)

  def sendEvent(self, clientId, channel, evt):
    response = {'channel': channel,
                'data': evt.__dict__
                }
    client = cometClients[clientId]
    client.write(response)
    client.finish()


  def sendPacket(self, name, id, data=None):
    if isinstance(id, int):
      id = str(id)
    if data:
      self.packets.append((id, name, data))
    else:
      self.packets.append((id, name))

  def flush(self):
    if self.packets:
      self.write(self.packets)
      self.packets = []
    if self.heartbeatTimer:
      self.heartbeatTimer.cancel()
      self.resetHeartbeat()

  # i don't think this is ever called...
  def finished(self, arg):
    logger.debug('finished: %s'%(arg,))
    self.request = None
    self.close()

  def onClose(self):
    logger.debug('onClose called')
    return self.closeDeferred

  def close(self):
    if self.closed:
      logger.debug('close called - already closed')
      return
    self.closed = True
    logger.debug('close ', repr(self))
    self.heartbeatTimer.cancel()
    self.heartbeatTimer = None
    self.open = False
    if self.request:
      logger.debug('calling finish')
      self.request.finish()
    self.request = None
    self.closeDeferred.callback(self)
    self.closeDeferred = None

  # Override these
  def write(self, packets):
    raise Exception("NotImplemented")

  def opened(self):
    raise Exception("NotImplemented")

  def writeHeartbeat(self):
    raise Exception("NotImplemented")  
  
  
class CometdFactory(channel.HTTPFactory):
  def __init__(self, parent):
    self.parent = parent
    channel.HTTPFactory.__init__(self, self.parent.site)

class CometdService(ConfigurableTCPServer):
  rootFactory = CometdWebResource
  factory = CometdFactory

  def __init__(self, service, *args, **kw):
    self.service = service
    self.root = self.rootFactory(self, service)
    self.site = server.Site(self.root)
    
    super(CometdService, self).__init__(*args, **kw)

