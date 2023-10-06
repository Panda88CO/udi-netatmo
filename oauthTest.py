
#!/usr/bin/env python3
"""
Polyglot v3 node server
Copyright (C) 2023 Universal Devices

MIT License
"""

import sys
import traceback
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

from NetatmoOauth import NetatmoCloud
#from nodes.controller import Controller
#from udi_interface import logging, Custom, Interface

polyglot = None
myNetatmo = None
controller = None
class NetatmoController(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name, myNetatmo):
        super(NetatmoController, self).__init__(polyglot, primary, address, name)
        logging.setLevel(10)
        self.poly = polyglot
        self.myNetatmo = myNetatmo
        self.poly.subscribe(polyglot.STOP, self.stopHandler)
        self.poly.subscribe(polyglot.CUSTOMDATA, self.myNetatmo.customDataHandler)
        self.poly.subscribe(polyglot.CUSTOMNS, self.myNetatmo.customNsHandler)
        self.poly.subscribe(polyglot.CUSTOMPARAMS, self.myNetatmo.customParamsHandler)
        self.poly.subscribe(polyglot.OAUTH, self.oauthHandler)
        self.poly.subscribe(polyglot.CONFIGDONE, self.configDoneHandler)
        self.poly.subscribe(polyglot.ADDNODEDONE, self.addNodeDoneHandler)


    def configDoneHandler(self):
        # We use this to discover devices, or ask to authenticate if user has not already done so
        self.poly.Notices.clear()

        accessToken = NetatmoCloud.getAccessToken()

        if accessToken is None:
            logging.info('Access token is not yet available. Please authenticate.')
            polyglot.Notices['auth'] = 'Please initiate authentication'
            return

        self.poly.discoverDevices()

    def oauthHandler(self, token):
        # When user just authorized, we need to store the tokens
        self.myNetatmo.oauthHandler(token)

        # Then proceed with device discovery
        self.configDoneHandler()


    def addNodeDoneHandler(self, node):
        # We will automatically query the device after discovery
        self.poly.addNodeDoneHandler(node)

    def stopHandler(self):
        # Set nodes offline
        for node in polyglot.nodes():
            if hasattr(node, 'setOffline'):
                node.setOffline()
        polyglot.stop()

id = 'controller'

drivers = [
        {'driver': 'ST', 'value':0, 'uom':2},
        ]

if __name__ == "__main__":
    try:
        logging.info ('starting')
        logging.info('Starting TeslaEV Controller')
        polyglot = udi_interface.Interface([])
        #polyglot.start('0.2.31')

        polyglot.start({ 'version': '0.0.1', 'requestId': True })

        # Show the help in PG3 UI under the node's Configuration option
        polyglot.setCustomParamsDoc()

        # Update the profile files
        polyglot.updateProfile()

        # Implements the API calls & Handles the oAuth authentication & token renewals
        myNetatmo= NetatmoCloud(polyglot)

        # then you need to create the controller node
        NetatmoController(polyglot, 'controller', 'controller', 'Netatmo', myNetatmo)

        # subscribe to the events we want
        # polyglot.subscribe(polyglot.POLL, pollHandler)

        # We can start receive events
        polyglot.ready()

        # Just sit and wait for events
        polyglot.runForever()

    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)

    except Exception:
        logging.error(f"Error starting Nodeserver: {traceback.format_exc()}")
        polyglot.stop()



