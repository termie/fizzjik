#from twisted.application import service

from fizzjik import hub

class Patch(hub.ConfigurableHub):
    """Transforms evts into others"""

    def __init__(self, default=None):
        hub.ConfigurableHub.__init__(self)
        if callable(default):
            self._patch_default = default

    def observe(self, evt):
        name = evt.__class__.__name__
        f = getattr(self, "_patch_%s"%(name), self._patch_default)
        self.parent.observe(f(evt))

    def _patch_default(self, evt):
        return evt
