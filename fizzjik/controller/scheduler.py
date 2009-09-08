


from twisted.internet import task


from fizzjik.config import ConfigurableService, if_config

    

class Scheduler(ConfigurableService):
    callback = None
    pollInterval = 60
    startDelayed = False

    def __init__(self, action):
        self.poller = task.LoopingCall(self.poll)
    

    def startService(self):
        service.Service.startService(self)
        self.poller.start(self.pollInterval, not self.startDelayed)

    def stopService(self):
        service.Service.stopService(self)
        if self.poller.running:
            self.poller.stop()
    
    def poll(self):
        if self.callback:
            self.callback()
