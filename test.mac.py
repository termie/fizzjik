#from fizzjik import cocoareactor
#cocoareactor.install()

from twisted.application import service

import fizzjik.input.easyident
import fizzjik.input.sonmicro
import fizzjik.input.basic

import fizzjik.output.basic
import fizzjik.output.lpr
import fizzjik.output.mplayer

from fizzjik.hub import Hub
#from fizzjik.input.easyident import EasyIdentSensor
from fizzjik.input.sonmicro import SonMicroMifareSensor
from fizzjik.input.btarduino import BTArduinoSensor
#from fizzjik.input.bluetooth import BluetoothSensor
from fizzjik.input.basic import LineReceiver
from fizzjik.input.network import NetworkConnectionSensor

from fizzjik.output.basic import Echo
from fizzjik.output.lpr import LPRService
#from fizzjik.output.growl import GrowlService

#from fizzjik.controller.network import DHClientController

#from fizzjik.patch import Patch

application = service.Application('easyident')

hub = Hub("test.mac.cfg")
hub.setServiceParent(application)

#bluey = BluetoothSensor()
#bluey.setServiceParent(hub)


#from fizzjik.event import Event
#def _tagAddedToNo(evt):
#    if evt.__class__.__name__ == "TagAddedEvent":
#        return Event("blaaaa")
#    else:
#        return evt

#patch_0 = Patch(_tagAddedToNo)
#patch_0.setServiceParent(hub)

#sonmicro_0 = SonMicroMifareSensor()
#sonmicro_0.setServiceParent(patch_0)
#sonmicro_0.setServiceParent(hub)

btarduino_0 = BTArduinoSensor()
btarduino_0.setServiceParent(hub)

#sonmicro_1 = SonMicroMifareSensor()
#sonmicro_1.setServiceParent(hub)
#easyident = EasyIdentSensor()
#easyident.setServiceParent(hub)

#network = NetworkConnectionSensor()
#network.setServiceParent(hub)

echo = Echo()
echo.setServiceParent(hub)

#dhclient = DHClientController()
#dhclient.setServiceParent(hub)

#growler = GrowlService()
#growler.setServiceParent(hub)

#hub.addObserver("TagAddedEvent", growler.defaultNotify)

lr = LineReceiver(2336)
lr.setServiceParent(hub)
