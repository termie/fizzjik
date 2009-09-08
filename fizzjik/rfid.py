from fizzjik.event import Event

class TagEvent(Event):
    def __init__(self, tag):
        self.data = tag

class TagAddedEvent(TagEvent):
    pass

class TagPresentEvent(TagEvent):
    pass

class TagRemovedEvent(TagEvent):
    pass
