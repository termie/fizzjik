import os

from twisted.application import service
from twisted.internet import protocol, reactor


from fizzjik.interfaces import IOutput, IConfigurable, implements
from fizzjik.config import ConfigurableMixin, if_config

class BrowserProcessProtocol(protocol.ProcessProtocol):
    posix_exec = 'firefox'
    posix_args = ['firefox']

    mac_exec = "open"
    mac_args = ["open"]

    def __init__(self, platform="posix"):
        self.platform = platform

    def connectionMade(self):
        print "connection made..."

    def spawn(self, *args):
        self.running = True
        reactor.spawnProcess(self, self.getExec(), args=self.getArgs()+list(args), env=os.environ)

    def kill(self):
        self.transport.signalProcess('KILL')

    def processEnded(self, reason):
        print reason
    
    def outReceived(self, line):
        print "\n".join(["out >> %s"%(x) for x in line.splitlines()])
    
    def errReceived(self, line):
        print "\n".join(["err !! %s"%(x) for x in line.splitlines()])
   
    def getExec(self):
        return getattr(self, '%s_exec'%(self.platform))
    
    def getArgs(self):
        return getattr(self, '%s_args'%(self.platform))

    def browse(self, url):
        print "url", url
        self.spawn(url)

class BrowserService(service.Service, ConfigurableMixin):
    implements(IOutput)
    
    enabled = True
    platform = "posix"

    @if_config('enabled')
    def startService(self):
        print "broaaz"
        self.browser = BrowserProcessProtocol(self.platform)
        pass

    def stopService(self):
        pass
    
    def browse(self, url):
        self.browser.browse('%s'%url)


    def stop(self):
        self.browser.stop()


