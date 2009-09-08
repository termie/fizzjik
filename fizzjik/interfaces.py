from zope.interface import Interface, Attribute, implements

class IEvent(Interface):
    data = Attribute("the data of the event")
    def match(cls):
        """whether this event can be handled by cls"""

class IConfigurable(Interface):
    """configurablee"""
    def receiveConfig(self, config):
        """stuff"""
        pass

class IInput(Interface):    
    """a service that sends events to the hub"""

class IController(Interface):
    """ controller blah blah"""
    def registerObservers(self, hub):
        """dovc"""

class IOutput(Interface):
    """ dunno yet"""

class IObserver(Interface):
    pass

class IMediaOutput(IOutput):
    """ some media stufff """

class IRemote(Interface):
    """ access a remote resource """

class ISensor(Interface):
    """ a class that interfaces with a sensor"""

class IMultiSensor(ISensor):
    """ a sensor that can sense multiple things at once """
