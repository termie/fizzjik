from fizzjik.config import ConfigurableTCPServer, ConfigurableService, \
        if_config, public_method
from fizzjik import process


class DiskFreeProcessProtocol(process.ProcessProtocol):
  mac_exec = 'df'
  mac_args = ['df', '-h']

  posix_exec = 'df'
  posix_args = ['df', '-h']



class FilesystemService(ConfigurableService):
  platform = "mac"

  @public_method
  def getFile(self, path):
    f = open(path)
    out = []
    for line in f:
      out.append(line.decode('utf8', 'replace'))
    return out

  @public_method
  def getLog(self, path):
    f = open(path)
    out = []
    for line in f:
      out.insert(0, line.decode('utf8', 'replace'))
    return out


  @public_method
  def getDiskFree(self):
    p = DiskFreeProcessProtocol(self.platform)
    d = p.spawn()
    return p.outDeferred
