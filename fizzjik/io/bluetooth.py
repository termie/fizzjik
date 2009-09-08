import re

from twisted.internet import defer, task, reactor
from twisted.application import service

import lightblue
import lightblue.obex


from fizzjik.config import ConfigurableService, ConfigurableMixin, if_config

import AppKit
import Foundation
from PyObjCTools.AppHelper import NSDefaultRunLoopMode


class BluetoothSensor(ConfigurableService):

    def __init__(self):
        self.poller = task.LoopingCall(self.poll)
    
    @if_config("enabled")
    def startService(self):
        ConfigurableService.startService(self)
        self.poller.start(30, True)
        #self.receiveFile()

    @if_config("enabled")
    def stopService(self):
        ConfigurableService.stopService(self)
        if self.poller.running:
            self.poller.stop()

    def poll(self):
        print "POLL"
        return self.findDevices(self.deviceFound)

    def findDevices(self, foundDevice=None, timeout=10):
        inquiry = lightblue.AsyncDeviceInquiry.alloc().init()

        d = defer.Deferred()
        
        def _completed(err, aborted):
            print "COMPLETE"
            d.callback((err, aborted))
        
        inquiry.cb_completed = _completed
        inquiry.cb_founddevice = foundDevice
        inquiry.length = timeout
        
        started = inquiry.start()
        
        if started != 0:
            return defer.fail(Exception("Failed to start %s" % started))
        
        reactor.callLater(timeout, inquiry.stop)

        return d

    def receiveFile(self, channel=0):
        sock = lightblue.socket()
        sock.bind(("", channel))
        channelID = sock._getport()

        print "receivee", sock, channelID
        
        lightblue.advertise("LightBlue example OBEX service", sock, lightblue.OBEX)

        server = lightblue.obex.OBEXServer.alloc().initWithChannel_(channelID)
        
        d_connected = defer.Deferred()
        d_disconnected = defer.Deferred()
        d_putcompleted = defer.Deferred()
        d_putrequested = defer.Deferred()
        d_errored = defer.Deferred()
        
        _fileobj = None

        def _putrequested(session, filename, filetype, filesize):
            print "req"
            _fileobj = open("tmp.tmp", "wb")
            filehandle = Foundation.NSFileHandle.alloc().initWithFileDescriptor_(f.fileno())
            d_putrequested.callback((session, filename, filetype, filesize))
            return filehandle
        
        def _disconnected(session):
            print 'disc'
            d_disconnected.callback(session)
        
        def _putcompleted(session):
            print "aooa"
            d_putcompleted.callback(session)
            _fileobj.close()

        def _errored(session, e, em):
            print session, e, em

        def _connected(session):
            print session
            d_connected.callback(session)

        server.disconnected = _disconnected
        server.putcompleted = _putcompleted
        server.putrequested = _putrequested
        server.errored = _errored
        server.connected = _connected
        
        #d_connected.addCallback(_putFile)
        #d_connected.addErrback(_handleError)
        #d_putcompleted.addCallback(_disconnect)
        #d_putcompleted.addErrback(_handleError)
        #d_disconnected.addBoth(_close)
        
        server.start()
        

    def sendFile(self, address, channel, source, timeout=10.0, connectTimeout=30.0):
        device = self.getConnection(address)
        client = lightblue.obex.OBEXClient.alloc().init()
        
        
        d_connected = defer.Deferred()
        d_disconnected = defer.Deferred()
        d_putcompleted = defer.Deferred()
        
        def _connected(e, em):
            d_connected.callback((e, em))
        
        def _disconnected(e, em):
            d_disconnected.callback((e, em))
        
        def _putcompleted(e, em):
            d_putcompleted.callback((e, em))

        client.connected = _connected
        client.disconnected = _disconnected
        client.putcompleted = _putcompleted
        
        def _putFile(rv):
            client.putfile(source)
            return True
        
        def _handleError(e):
            print "error", e
            client.disconnect()

        def _disconnect(e):
            print "Discconnecting"
            client.disconnect()

        def _close(e):
            print "CLOOSSE"
            client.close()
            device.closeConnection()

        d_connected.addCallback(_putFile)
        d_connected.addErrback(_handleError)
        d_putcompleted.addCallback(_disconnect)
        d_putcompleted.addErrback(_handleError)
        d_disconnected.addBoth(_close)

        try:
            client.connect(address, channel)
        except Exception, e:
            device.closeConnection()




    def getConnection(self, address):
        return lightblue._IOBluetooth.IOBluetoothDevice.withAddress_(
                    lightblue._macutil.btaddrtochars(address))

    # callbacks
    def deviceFound(self, device):
        addr = device.getAddressString()
        addr = addr.replace("-", ":").encode('ascii').upper()
        name = device.getName()
        cod = device.getClassOfDevice()
        
        dev = {"address": addr,
               "name": name,
               "classOfDevice": cod,
               "services": {}}
        services = device.getServices()
        if not services: services = []
        for s in services:
            s_name = s.getServiceName()
            result, channel = s.getRFCOMMChannelID_()
            if result != lightblue._macutil.kIOReturnSuccess:
                result, channel = s.getL2CAPPSM_()
                if result != lightblue._macutil.kIOReturnSuccess:    
                    channel = None
            dev['services'][s_name] = {"channel": channel, "address": addr}
                

        if "OBEX File Transfer" in dev['services']:
            def _sendTest():
                print "SENDING"
                source = u"hello.txt"
                self.sendFile(dev['address'], dev['services']['OBEX File Transfer']['channel'], source)
            print "Call me later"
            #reactor.callLater(10, _sendTest)
            #_sendTest()

        print dev
        #print sevices

if __name__ == "__builtin__":
    from twisted.application import internet, service

    application = service.Application("asdf")
    
    bt = BluetoothSensor()
    bt.setServiceParent(application)
