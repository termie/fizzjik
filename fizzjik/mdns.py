# EXPERIMENTAL
import _zeroconf as zeroconf

import re

###
from twisted.internet import protocol, udp
from twisted.internet import reactor
from twisted.application.internet import MulticastServer

class SubscriberProxy(object):
    def __init__(self, svc, subscriber):
        self._proxy = subscriber
        self._svc = svc

    def recordAdded(self, record):
        self._proxy.serviceAdded(self._svc, record.name, record.alias)

    def recordRemoved(self, record):
        self._proxy.serviceRemoved(self._svc, record.name, record.alias)


class Cache(zeroconf.Cache):
    def __init__(self):
        super(Cache, self).__init__()
        self._timers = {}
    
    def append(self, record):
        super(Cache, self).append(record)
        self.bumpTimer(record)

    def update(self, record):
        record = super(Cache, self).update(record)
        self.bumpTimer(record)
        return record

    def bumpTimer(self, record):
        if record in self._timers.keys():
            self._timers[record].cancel()
        else:
            #print 'adding timer', record.name.encode("ascii", "replace"), record.ttl / 1000
            pass
        self._timers[record] = reactor.callLater(record.ttl / 1000, self._recordExpired, record)

    def _recordExpired(self, record):
        del self._timers[record]
        self.remove(record)

class ZeroconfProtocol(protocol.DatagramProtocol):
    def __init__(self, parent, *args, **kw):
        self.parent = parent

    def datagramReceived(self, data, addr):
        addr, port = addr
        msg = zeroconf.DNSIncoming.parse(data)

        if msg.isQuery():
            self.parent.handleQuery(msg, addr, port)
        else:
            self.parent.handleResponse(msg)

    def startProtocol(self):
        d = self.transport.joinGroup(zeroconf.MDNS_ADDR)
        def pr(s):
            print "joined mdns group"
        d.addCallback(pr)
        
class ZeroconfService(MulticastServer):
    """ 
    will listen for mDNS stuff, and provides the tools to add services or fire
    callbacks when stuff is received
    """
    cache = None
    services = None
    listeners = None
    subscriptions = None

    
    protocol = ZeroconfProtocol
    
    def __init__(self):
        self.inst = self.protocol(self)
        MulticastServer.__init__(self, zeroconf.MDNS_PORT, self.inst, 
                                 listenMultiple=True)
        self.cache = Cache()
        self.services = []
        self.listeners = {}
        self.subscriptions = {}
        
    def startService(self, *args, **kw):
        MulticastServer.startService(self, *args, **kw)
        reactor.callLater(5, self.query, zeroconf.DNSQuestion('_daap._tcp.local.', zeroconf.TYPE_PTR))

    # high level
    def publishService(self, service):
        pass

    def unpublishService(self, service):
        pass

    def subscribeService(self, type, subscriber):
        if not type.endswith(zeroconf.LOCAL_NAME):
            dns_type = "_%s._tcp.local."%(type)

        subscriberProxy = SubscriberProxy(self, subscriber)

        self.subscriptions[subscriber] = subscriberProxy

        self.addSubscription(zeroconf.DNSQuestion(dns_type, zeroconf.TYPE_PTR), 
                             subscriberProxy)

    def unsubscribeService(self, type, subscriber):
        if not type.endswith(zeroconf.LOCAL_NAME):
            dns_type = "_%s._tcp.local."%(type)
        self.removeSubscription(zeroconf.DNSQuestion(dns_type, zeroconf.TYPE_PTR), 
                                      self.subscriptions[subscriber])
    
    def addSubscription(self, question, subscriber):
        # add this to our list of subscriptions for the given question
        # check if we already have an answer to this in our cache
        pass

    def removeSubscription(self, question, subscriber):
        # remove this from our list of subscriptions
        pass

    def getServices(self, type, timeout=2):
        """ 
        return a deferred that is calledback with a list of services once
        they have returned
        """
        pass
    

    # low level
    def addListener(self, question, listener):
        """ listens for specific responses """
        if question not in self.listeners.keys():
            self.listeners[question] = []
        self.listeners[question].append(listener)

    def removeListener(self, question, listener):
        self.listeners[question].remove(listener)

    def query(self, question):
        print "querying"
        out = zeroconf.DNSOutgoing(zeroconf.FLAGS_QR_QUERY)
        out.addQuestion(question)
        self.send(out.packet())

    def send(self, packet):
        self.inst.transport.write(packet, (zeroconf.MDNS_ADDR, zeroconf.MDNS_PORT))

    def notifyListeners(self, record):
        for question in self.listeners.keys():
            if question.answeredBy(record):
                for f in self.listeners[question]:
                    f(record)
    
    # event handlers
    def handleQuery(self, msg, addr, port):
        """ respond to a query if we can """
        #for q in msg.questions:
        #    print "q", q.name.encode("ascii", "replace"), q.type
        pass

    def handleResponse(self, msg):
        """ probably update a record """
        now = zeroconf.now()

        for a in msg.answers:
            expired = a.isExpired(now)
            if a in self.cache:
                if expired:
                    self.cache.remove(a)
                else:
                    a = self.cache.update(a)
            elif not expired:
                self.cache.append(a)

                print "a", a.name.encode("ascii", "replace"), a.type,
                if a.type == "a":
                    print a.address,
                elif a.type == "srv":
                    print a.port, a.server,
                else:
                    print getattr(a, "alias", "?").encode("ascii", "replace"),
                print a.ttl / 1000
            self.notifyListeners(a)


"""
class ServiceTracker(object):
    def serviceAdded(self, zc, type, name):
        pass
    def serviceRemoved(self, zc, type, name):
        pass


zc = ZeroconfService()
zc.subscribeService("daap", ServiceTracker())
"""
    
if __name__ == "__builtin__":
    from twisted.application import service, internet
    application = service.Application("mdns")
    
    
    def printDaapPtr(ptr):
        print "aaaa", ptr.alias.encode("ascii", "replace")
        #print "aaaa"

    def printUserPass(any):
        print "weee", any.name.encode("ascii", "replace")
        #print "weee"


    mdns = ZeroconfService()
    mdns.setServiceParent(application)

    #mdns.addListener(zeroconf.DNSQuestion('_daap._tcp.local.', zeroconf.TYPE_PTR, zeroconf.CLASS_IN), printDaapPtr)

    #mdns.addListener(zeroconf.DNSQuestion('User/Pass?._daap._tcp.local.', zeroconf.TYPE_ANY, zeroconf.CLASS_IN), printUserPass)

    class Subber(object):
        def serviceAdded(self, zc, type, name):
            print "service added!", type, name.encode("ascii", "replace")
            pass

        def serviceRemoved(self, zc, type, name):
            print "service remmd!", type, name.encode("ascii", "replace")
            pass

    subb = Subber()
    mdns.subscribeService("daap", subb)
