import random

from fizzjik.config import ConfigurableMixin, if_config, public_method
from fizzjik.io.say import SayService

class CurseService(SayService):
    curses_path = "curses.dict"
  
    @if_config('enabled')
    def startService(self):
      SayService.startService(self)
      self.curses = self._loadCurses(self.curses_path)

    def _loadCurses(self, path):
      f = open(path)
      curses = f.readlines()
      f.close()
      return curses

    @public_method
    def curse(self):
      curse = self.getCurse()
      self.say(curse)

    @public_method
    def getCurse(self):
      return random.choice(self.curses).strip()
