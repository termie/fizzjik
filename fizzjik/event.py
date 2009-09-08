from fizzjik.interfaces import IEvent, implements

class Event(object):
    implements(IEvent)

    def __init__(self, data=None):
        self.data = data

    def __repr__(self):
        return "<%s: data=%s>"%(self.__class__.__name__, self.data)

    def match(self, cls):
        if type(cls) is type("") or type(cls) is type(u""):
            return cls == self.__class__.__name__
        if isinstance(self, cls):
            return True
        return False

class ExceptionEvent(Event):
    pass

class ServiceStartEvent(Event):
    pass

class ServiceStopEvent(Event):
    pass

class InputEvent(Event):
    pass

class InputAddedEvent(InputEvent):
    pass
class InputPresentEvent(InputEvent):
    pass
class InputRemovedEvent(InputEvent):
    pass
