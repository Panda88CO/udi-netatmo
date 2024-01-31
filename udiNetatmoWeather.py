#!/usr/bin/env python3

"""
Polyglot v3 node server
Copyright (C) 2023 Universal Devices

MIT License
"""


import time
import traceback
import re
import sys

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

#from NetatmoOauth import NetatmoCloud
from NetatmoWeather import NetatmoWeather
from  udiNetatmoWeatherMain import udiNetatmoWeatherMain
#from nodes.controller import Controller
#from udi_interface import logging, Custom, Interface
version = '0.0.7'

#polyglot = None
#myNetatmo = None
#controller = None

#id = 'controller'
#drivers = [
#        {'driver': 'ST', 'value':0, 'uom':2},
#        ]

class NetatmoController(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name):
        super(NetatmoController, self).__init__(polyglot, primary, address, name)
        logging.debug('NetatmoController Initializing')
        logging.setLevel(10)
        self.poly = polyglot
        self.id = 'controller'
        self.drivers =  [ {'driver': 'ST', 'value':0, 'uom':2}, ]
        self.accessTokenEn = True
        self.accessToken = None
        self.nodeDefineDone = False
        self.configDone = False
        self.name = name
        self.primary = primary
        self.address = address
        self.temp_unit = 0
        self.myNetatmo = NetatmoWeather(self.poly)
        self.hb  = 0
        logging.debug('testing 1')
        self.customParameters = Custom(self.poly, 'customparams')
        self.Notices = Custom(self.poly, 'notices')
        self.n_queue = []
        logging.debug('drivers : {}'.format(self.drivers))
        self.poly.subscribe(self.poly.STOP, self.stopHandler)
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.myNetatmo.customParamsHandler)
        #self.poly.subscribe(self.poly.CUSTOMDATA, self.myNetatmo.customDataHandler)
        self.poly.subscribe(self.poly.CUSTOMNS, self.myNetatmo.customNsHandler)
        self.poly.subscribe(self.poly.OAUTH, self.myNetatmo.oauthHandler)
        self.poly.subscribe(self.poly.CONFIGDONE, self.configDoneHandler)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.addNodeDoneHandler)
        self.poly.subscribe(self.poly.POLL, self.systemPoll)

        logging.debug('testing 2')

        self.poly.addNode(self)
        logging.debug('drivers : {}'.format(self.drivers))
        logging.debug('testing 3')
        #self.wait_for_node_done()
        logging.debug('testing 4')
        self.node = self.poly.getNode(self.address)
        logging.debug(' Node: {}'.format(self.node))
        logging.debug('testing 5')
        self.poly.updateProfile()
        self.poly.ready()
       

    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()

    def getValidName(self, name):
        name = bytes(name, 'utf-8').decode('utf-8','ignore')
        return re.sub(r"[^A-Za-z0-9_ ]", "", name)

    # remove all illegal characters from node address
    def getValidAddress(self, name):
        name = bytes(name, 'utf-8').decode('utf-8','ignore')
        tmp = re.sub(r"[^A-Za-z0-9_]", "", name.lower())
        logging.debug('getValidAddress {}'.format(tmp))
        return tmp[:14]
    

    def convert_temp_unit(self, tempStr):
        if tempStr.capitalize()[:1] == 'F':
            return(1)
        elif tempStr.capitalize()[:1] == 'C':
            return(0)
   
    def heartbeat(self):
        logging.debug('heartbeat: ' + str(self.hb))
        #if self.yoAccess.online:
        #    self.node.setDriver('ST', 1)
        #    if self.hb == 0:
        #       self.reportCmd('DON',2)
        #       self.hb = 1
        #   else:
        #       self.reportCmd('DOF',2)
        #       self.hb = 0
        #else:
        #    self.node.setDriver('ST', 0)
        

    def start(self):
        logging.info('Executing start')
        #self.myNetatmo = NetatmoWeather(self.poly)
        #self.accessToken = self.myNetatmo.getAccessToken()
        #logging.debug('Waiting start: {} {} {}'.format(self.configDone, self.myNetatmo.customParamsDone(), self.myNetatmo.customNsDone()))
        while not (self.configDone and self.myNetatmo.customParamsDone() and self.myNetatmo.customNsDone()):
        #while not (self.configDone):
            time.sleep(2)
            logging.debug('Waiting for config to complete {} {} {}'.format(self.configDone, self.myNetatmo.customParamsDone(),  self.myNetatmo.customNsDone()))
        #time.sleep(1)
        #if self.refreshToken and self.client_ID and self.client_SECRET:
        #    self.myNetatmo._insert_refreshToken(self.refreshToken, self.client_ID, self.client_SECRET)
        #    logging.debug('AccessToken = {}'.format(self.accessToken))

            
        while not self.myNetatmo.authendicated():
            logging.warning('Access token is not yet available. Please authenticate.')
            self.poly.Notices['auth'] = 'Please initiate authentication'
            time.sleep(5)            

        
        time.sleep(1)
        self.poly.Notices.clear()    

        self.home_ids = self.myNetatmo.get_homes()
        if self.home_ids:
            self.node.setDriver('ST', 1, True, True)

        self.temp_unit = self.convert_temp_unit(self.myNetatmo.temp_unit)
        logging.debug('TEMP_UNIT: {}'.format(self.temp_unit ))


        self.addNodes()
        


    def addNodes(self):

        logging.info('Adding selected weather stations')
        selected = False
        self.enabled_list = []
        self.homes_list = []
        for home in self.home_ids:
            logging.debug('Adding from {}'.format(home))
            home_name = self.home_ids[home]['name']
            main_modules = self.myNetatmo.get_main_modules(home)
            for m_module in main_modules:
                logging.debug('adding MAIN modules {} - {}'.format(m_module, main_modules))
                mod_name = main_modules[m_module]['name']
                node_name = home_name + '_'+ mod_name
                tmp = {}
                tmp['home'] = home
                tmp['main_module'] = m_module
                if node_name in self.customParameters:
                    if self.customParameters[node_name] == 1:
                        self.enabled_list.append(tmp)
                        logging.debug('enabled list {}'.format(self.enabled_list))
                        if tmp['home'] not in self.homes_list:
                            self.homes_list.append(tmp['home'])
                            self.myNetatmo.update_weather_info_cloud(home)
                            self.myNetatmo.update_weather_info_instant(home)
                        selected = True
                else:
                    self.customParameters[node_name] = 1 #enable by default
                    self.enabled_list.append(tmp)
                    logging.debug('enabled list - else {}'.format(self.enabled_list))
                    if tmp['home'] not in self.homes_list:
                        self.homes_list.append(tmp['home'])
                        self.myNetatmo.update_weather_info_cloud(home)
                        self.myNetatmo.update_weather_info_instant(home)

        if not selected and len(self.home_ids) > 1:
            self.poly.Notices['home_id'] = 'Check config to select which home/modules should be used (1 - used, 0 - not used) - then restart'
        else:
            logging.debug('enabled list - outside {}'.format(self.enabled_list))
            for node_nbr in range(0,len(self.enabled_list)):
                module_info = self.enabled_list[node_nbr]
                logging.debug('module_info {}'.format(module_info))
                if module_info['home'] not in self.homes_list:
                    self.homes_list.append(module_info['home'])
                module = self.myNetatmo.get_module_info(module_info['home'],module_info['main_module'])
                logging.debug('module info {}'.format(module))
                node_address = self.getValidAddress(module['id'])
                node_name = self.getValidName(module['name'])
                logging.debug('names: {} {}, Addresses {} {}'.format(module['name'],node_name , module['id'], node_address  ))
                if not udiNetatmoWeatherMain(self.poly, node_address, node_address, node_name, self.myNetatmo, module_info):
                    logging.error('Failed to create Main Weather station: {}'.format(node_name))
                time.sleep(1)            

        self.nodeDefineDone = True

    
    def configDoneHandler(self):
        # We use this to discover devices, or ask to authenticate if user has not already done so
        self.poly.Notices.clear()
        logging.info('configDoneHandler called')
        #self.myNetatmo.updateOauthConfig()
        
        self.configDone = True
        
        #res = self.myNetatmo.get_home_info()
        #logging.debug('retrieved get_home_info data {}'.format(res))

        #res = self.myNetatmo.get_weather_info()
        #logging.debug('retrieved get_weather_info data {}'.format(res))

        #res = self.myNetatmo.get_weather_info2()
        #logging.debug('retrieved get_weather_info2 data2 {}'.format(res))

        #self.poly.discoverDevices()

    def addNodeDoneHandler(self, node):
        pass
        # We will automatically query the device after discovery
        #self.poly.addNodeDoneHandler(node)
        #self.nodeDefineDone = True

    def systemPoll (self, polltype):
        if self.nodeDefineDone:
            logging.info('System Poll executing: {}'.format(polltype))
            nodes = self.poly.nodes()
            #logging.debug('nodes : {}'.format(nodes))
            try:
                if 'longPoll' in polltype:
                    #Keep token current
                    #self.node.setDriver('GV0', self.temp_unit, True, True)
                    
                        #self.myNetatmo.refresh_token()
                        for home in self.homes_list:
                            self.myNetatmo.update_weather_info_cloud(home)
                            self.myNetatmo.update_weather_info_instant(home)


                        #nodes = self.poly.getNodes()
                        for nde in nodes:
                            if nde.address != 'controller':   # but not the setup node
                                logging.debug('updating node {} data'.format(nde))
                                nde.updateISYdrivers()
                                                
                if 'shortPoll' in polltype:
                    self.heartbeat()
                    #self.myNetatmo.refresh_token()
                    for home in self.homes_list:
                        self.myNetatmo.update_weather_info_instant(home)
                    for nde in nodes:
                        if nde.address != 'controller':   # but not the setup node
                            logging.debug('updating node {} data'.format(nde))
                            nde.updateISYdrivers()                   
            except Exception as e:
                    logging.error('Exeption occcured : {}'.format(e))
   
                
        else:
            logging.info('System Poll - Waiting for all nodes to be added')
 

    def stopHandler(self):
        # Set nodes offline
        for node in self.poly.nodes():
            if hasattr(node, 'setOffline'):
                #node.setDriver('ERR', 1)
                node.setOffline()
        self.poly.stop()


if __name__ == "__main__":
    try:
        logging.info ('starting')
        logging.info('Starting Netatmo Controller')
        polyglot = udi_interface.Interface([])
        #polyglot.start('0.2.31')

        polyglot.start({ 'version': version, 'requestId': True })

        # Show the help in PG3 UI under the node's Configuration option
        polyglot.setCustomParamsDoc()

        # Update the profile files
        #polyglot.updateProfile()

        # Implements the API calls & Handles the oAuth authentication & token renewals
        #myNetatmo = NetatmoWeather(polyglot)

        # then you need to create the controller node
        NetatmoController(polyglot, 'controller', 'controller', 'Netatmo')

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



