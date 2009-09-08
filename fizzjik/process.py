# vim: softtabstop=4 shiftwidth=4
import os
import logging

from twisted.application import service
from twisted.internet import protocol, reactor, defer
from twisted.internet import error


#from fizzjik.interfaces import IOutput, implements
from fizzjik.config import ConfigurableMixin, if_config

class ProcessProtocol(protocol.ProcessProtocol):
    posix_exec = '/usr/bin/env'
    posix_args = ['/usr/bin/env']

    running = False
    outCallback = None
    errCallback = None
    outDeferred = None
    errDeferred = None
    startedDeferred = None
    endedDeferred = None
    out = None
    err = None

    def __init__(self, platform="posix", outCallback=None, errCallback=None):
        self.platform = platform
        self.outDeferred = defer.Deferred()
        self.errDeferred = defer.Deferred()
        self.startedDeferred = defer.Deferred()
        self.endedDeferred = defer.Deferred()
        

        self.endedDeferred.addErrback(self._handleCleanExit)
        self.endedDeferred.addErrback(self._handleUncleanExit)

        if not outCallback:
            outCallback = self.defaultOut
        self.outCallback = outCallback

        if not errCallback:
            errCallback = self.defaultErr
        self.errCallback = errCallback
        
        self.err = []
        self.out = []



    def connectionMade(self):
        self.running = True
        self.startedDeferred.callback(True)
        logging.debug("process started...")

    def spawn(self, *args):
        if not self.getExec():
            return
        reactor.spawnProcess(self, self.getExec(), args=self.getArgs()+list(args), env=os.environ)
        return self.startedDeferred

    def kill(self):
        if self.running:
            self.transport.signalProcess('KILL')

    def processEnded(self, reason):
        if not self.running:
            self.startedDeferred.errback(reason)
        self.endedDeferred.callback(reason)
        self.outDeferred.callback(self.out)
        self.errDeferred.callback(self.err)
        self.running = False

    def _handleCleanExit(self, reason):
        if not isinstance(reason.value, error.ProcessDone):
            return reason
        if reason.value.exitCode == 0:
            logging.debug('process ended cleanly')
            return True
        return reason

    def _handleUncleanExit(self, reason):
        logging.debug('process ended uncleanly: %s' % reason)
    
    def outReceived(self, line):
        for l in line.splitlines():
            self.out.append(l)
        self.outCallback(line)
    
    def errReceived(self, l):
        for l in line.splitlines():
            self.err.append(l)
        self.errCallback(line)

    @staticmethod
    def defaultErr(line):
        logging.debug("\n".join(["err !! %s"%(x) for x in line.splitlines()]))
    
    @staticmethod
    def defaultOut(line):
        logging.debug("\n".join(["out >> %s"%(x) for x in line.splitlines()]))

    def getExec(self):
        return getattr(self, '%s_exec'%(self.platform), None)
    
    def getArgs(self):
        return getattr(self, '%s_args'%(self.platform), None)


class ProcessService(service.Service, ConfigurableMixin):
    enabled = True
    platform = "posix"
    protocol = ProcessProtocol


    @if_config('enabled')
    def startService(self):
        self.process = self.protocol(self.platform)
        pass
    
    @if_config('enabled')
    def stopService(self):
        self.process.kill()
        pass
    
    def spawn(self, *args):
        self.process.spawn(*args)

