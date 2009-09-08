import os

from twisted.application import service
from twisted.internet import protocol, reactor


from fizzjik.interfaces import IMediaOutput, IConfigurable, implements
from fizzjik.config import ConfigurableMixin, if_config

class MPlayerProcessProtocol(protocol.ProcessProtocol):
    posix_exec = 'mplayer'
    posix_args = ['mplayer', '-slave', '-quiet', '-fs']
    mac_exec = '/Applications/MPlayer OSX.app/Contents/Resources/External_Binaries/mplayer.app/Contents/MacOS/mplayer'
    mac_args = ['/Applications/MPlayer OSX.app/Contents/Resources/External_Binaries/mplayer.app/Contents/MacOS/mplayer',
                '-slave', '-vo', 'quartz', '-fs', '-quiet']

    running = False
    last = None
    state = 0
    PLAYING = 1
    PAUSED = 2
    STOPPED = 0
    WAITING = -1

    def __init__(self, platform="posix"):
        self.platform = platform

    def connectionMade(self):
        print "connection made..."

    def spawn(self, *args):
        self.running = True
        self.state = self.PLAYING
        reactor.spawnProcess(self, self.getExec(), args=self.getArgs()+list(args), env=os.environ)

    def kill(self):
        #self.running = False
        self.transport.signalProcess('KILL')

    def processEnded(self, reason):
        self.state = self.STOPPED
        self.running = False
        print reason
    
    def outReceived(self, line):
        print "\n".join(["out >> %s"%(x) for x in line.splitlines()])
        #if line.startswith("status change:"):
        #    m = re.search("""state: (\d)""", line)
        #    if m:
        #        self.stateChanged(m.group(1))
    
    def errReceived(self, line):
        print "\n".join(["err !! %s"%(x) for x in line.splitlines()])
   
    def getExec(self):
        return getattr(self, '%s_exec'%(self.platform))
    
    def getArgs(self):
        return getattr(self, '%s_args'%(self.platform))

    def play(self, item=None):
        if item is None and self.state == self.PAUSED:
            self.unpause()
        elif item is self.last:
            if self.state == self.PAUSED:
                self.unpause()
            elif not self.running:
                self.spawn(item)
            else:
                self.transport.write('loadfile %s\n'%(item))
            return
        else:
            self.last = item
            if not self.running:
                self.spawn(item)
            else:
                self.state = self.PLAYING
                self.transport.write('loadfile %s\n'%(item))

    def stop(self):
        if self.state != self.STOPPED:
            self.transport.write('quit\n')
        
    def pause(self):
        if self.state == self.PLAYING:
            self.transport.write('pause\n')
            self.state = self.PAUSED
        return

    def unpause(self):
        if not self.running:
            return
        if self.state == self.PAUSED:
            self.transport.write('pause\n')
            self.state = self.PLAYING
        return

class MPlayerService(service.Service, ConfigurableMixin):
    implements(IMediaOutput)

    enabled = True
    platform = "posix"

    @if_config('enabled')
    def startService(self):
        print "I, mplayer, am teg loadsz"
        self.player = MPlayerProcessProtocol(self.platform)
        self.startServer()

    @if_config('enabled')
    def stopService(self):
        self.stopServer()
    
    def startServer(self):
        #if not self.vlc.running:
        #    self.vlc.spawn()
        pass

    def stopServer(self):
        if self.player.running:
            self.player.kill()

    def play(self, item=None):
        """
        ensure that stream is playing, if an argument is given ensure
        that it plays that
        """
        self.player.play(item)

    def pause(self, item=None):
        """ensure that stream is paused"""
        self.player.pause()

    def stop(self):
        """ensure that stream is stopped"""
        self.player.stop()


