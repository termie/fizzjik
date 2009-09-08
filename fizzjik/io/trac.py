import os

from twisted.application import service
from twisted.internet import protocol, reactor, defer
from twisted.internet import error

from fizzjik.interfaces import IOutput, IConfigurable, implements
from fizzjik.config import ConfigurableMixin, if_config

class TracProcessProtocol(protocol.ProcessProtocol):
    posix_exec = 'trac-admin'
    posix_args = ['trac-admin']

    mac_exec = "trac-admin"
    mac_args = ["trac-admin"]
    
    win_exec = 'C:\Python25\python.exe'
    win_args = ['C:\Python25\python.exe', 'C:\Python25\scripts\trac-admin']

    def __init__(self, platform="posix"):
        self.platform = platform
        self.buffer = []
        self.deferred = defer.Deferred()

    def connectionMade(self):
        print "connection made..."

    def spawn(self, *args):
        self.running = True
        reactor.spawnProcess(self, self.getExec(), args=self.getArgs()+list(args), env=os.environ)

    def kill(self):
        self.transport.signalProcess('KILL')

    def processEnded(self, reason):
        #self.deferred.callback(self.buffer)
        print reason, dir(reason)
        print "type", reason.type
        print "value", reason.value
        if reason.type == error.ProcessTerminated:
            self.deferred.errback(self.buffer)
        elif reason.type == error.ProcessDone:
            self.deferred.callback(self.buffer)
            
    
    def outReceived(self, line):
        self.buffer.append(line)
        print "\n".join(["out >> %s"%(x) for x in line.splitlines()])
    
    def errReceived(self, line):
        self.buffer.append(line)
        print "\n".join(["err !! %s"%(x) for x in line.splitlines()])
   
    def getExec(self):
        return getattr(self, '%s_exec'%(self.platform))
    
    def getArgs(self):
        return getattr(self, '%s_args'%(self.platform))

    def getPage(self, repo, tag):
        self.spawn(repo, "wiki", "export", tag)
        return self.deferred
class TracServerProcessProtocol(protocol.ProcessProtocol):
    posix_exec = 'tracd'
    posix_args = ['tracd', '-p', '8000', '-s']

    mac_exec = "tracd"
    mac_args = ["trac", '-p', '8000', '-s']
    
    win_exec = 'C:\Python25\python.exe'
    win_args = ['C:\Python25\python.exe', 'C:\Python25\scripts\tracd', '-p', '8000', '-s']
    
    def __init__(self, platform="posix"):
        self.platform = platform
        self.buffer = []
        self.deferred = defer.Deferred()

    def connectionMade(self):
        print "connection made..."

    def spawn(self, *args):
        self.running = True
        reactor.spawnProcess(self, self.getExec(), args=self.getArgs()+list(args), env=os.environ)

    def kill(self):
        self.transport.signalProcess('KILL')

    def processEnded(self, reason):
        #self.deferred.callback(self.buffer)
        print reason, dir(reason)
        print "type", reason.type
        print "value", reason.value
        if reason.type == error.ProcessTerminated:
            self.deferred.errback(self.buffer)
        elif reason.type == error.ProcessDone:
            self.deferred.callback(self.buffer)
            
    
    def outReceived(self, line):
        self.buffer.append(line)
        print "\n".join(["out >> %s"%(x) for x in line.splitlines()])
    
    def errReceived(self, line):
        self.buffer.append(line)
        print "\n".join(["err !! %s"%(x) for x in line.splitlines()])
   
    def getExec(self):
        return getattr(self, '%s_exec'%(self.platform))
    
    def getArgs(self):
        return getattr(self, '%s_args'%(self.platform))


class TracService(service.Service, ConfigurableMixin):
    implements(IOutput)
    
    enabled = True
    platform = "posix"
    repo = "trac"
    url = "localhost:8000"

    @if_config('enabled')
    def startService(self):
        self.tracserver = TracServerProcessProtocol(self.platform)
        self.tracserver.spawn(self.repo)
        pass

    def stopService(self):
        self.tracserver.kill()
        pass
    
    def getPage(self, tag):
        tr = TracProcessProtocol(self.platform)
        return tr.getPage(self.repo, tag)

    def stop(self):
        self.trac.stop()



