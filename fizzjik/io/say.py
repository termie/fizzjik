import os

from twisted.application import service
from twisted.internet import protocol, reactor, defer
from twisted.internet import error

from fizzjik.interfaces import IOutput, IConfigurable, implements
from fizzjik import config
from fizzjik import process

class SayProcessProtocol(process.ProcessProtocol):
  mac_exec = 'say'
  mac_args = ['say']

  posix_exec = None
  posix_args = None

  

class SayService(config.ConfigurableService):
  implements(IOutput)

  enabled = True
  platform = "mac"
  protocol = SayProcessProtocol


  @config.if_config('enabled')
  def startService(self):
    self.process = self.protocol(self.platform)

  @config.if_config('enabled')
  def stopService(self):
    self.process.kill()
  
  @config.public_method
  def say(self, phrase):
    self.spawn(phrase)

  def spawn(self, *args):
    self.process.spawn(*args)

  def kill(self):
    self.process.kill()
