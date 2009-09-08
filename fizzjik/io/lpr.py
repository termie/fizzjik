import os

from fizzjik.interfaces import IOutput, implements
from fizzjik.process import ProcessService, ProcessProtocol

class LPRProcessProtocol(ProcessProtocol):
    posix_exec = 'lpr'
    posix_args = ['lpr']

    def print_(self, f, *args):
        self.spawn(*args)
        data = f.read()
        self.transport.write(data)
        self.transport.closeStdin()

class LPRService(ProcessService):
    implements(IOutput)
    enabled = True
    platform = "posix"
    protocol = LPRProcessProtocol
    really_print = False

    def print_(self, f, *args):
        if self.really_print:
            self.process.print_(f, *args)
        else:
            print "would be printing:", 
            print f.name
