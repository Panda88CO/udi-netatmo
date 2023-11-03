
#!/usr/bin/env python3

from NetatmoOauthDev import NetatmoCloud
from NetatmoControlHC import NetatmoControlHC
from NetatmoControlLighting import NetatmoControlLighting
from NetatmoControlPower import NetatmoControlPower
from NetatmoControlShutter import NetatmoControlShutter
from NetatmoControlVentilation import NetatmoControlVentilation


import urllib.parse

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)
    


class NetatmoControl (NetatmoCloud):
    def __init__(self):
        super().__init__()
        self.instant_data = {}
        self.cloud_data = {}
        self.control_data = {}
