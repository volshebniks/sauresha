#Provides a sensor for Saures.
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval

from homeassistant.util import Throttle

from homeassistant.const import (
    CONF_EMAIL,  
    CONF_PASSWORD
)

import voluptuous as vol
import re
from datetime import timedelta

from . import (
    CONF_FLAT_ID, 
    CONF_COUNTERS_SN,
    CONF_CONTROLLERS_SN,
    CONF_SCAN_INTERVAL,
    CONF_DEBUG
)

import logging


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta (minutes = 10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_FLAT_ID): cv.positive_int,
    vol.Optional(CONF_COUNTERS_SN): cv.ensure_list,
    vol.Optional(CONF_CONTROLLERS_SN): cv.ensure_list,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL):
                vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_DEBUG,default=False): cv.boolean,
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None,scan_interval=SCAN_INTERVAL):
    """Setup the sensor platform."""

    from .sauresha import SauresHA
    
    flat_id = config.get(CONF_FLAT_ID)
    serial_numbers = config.get(CONF_COUNTERS_SN, [])
    sns = config.get(CONF_CONTROLLERS_SN, [])
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    is_debug = config.get(CONF_DEBUG)

    if is_debug:
        _LOGGER.warning("scan_interval=" + str(scan_interval))


    controller = SauresHA(
        config.get('email'),
        config.get('password')
    )

    if int(flat_id)==0: 
        flats=controller.get_flats()
        if len(flats)==1: 
            flat_id=str(flats[0].get('id'))
            strHouse = str(flats[0].get('house'))
            _LOGGER.warning("ID flat:" + strHouse + " : " + flat_id)
        else: 
            for val in flats:
                _LOGGER.warning("ID flat:" + str(val.get('house')) + " : " + str(val.get('id')))

    if int(flat_id)>0:        
        create_sensor = lambda serial_number: SauresSensor(hass, controller, flat_id, serial_number,is_debug,scan_interval)
        sensors = list(map(create_sensor, serial_numbers))

        if sensors: async_add_entities(sensors, True)

        create_myController = lambda sn: SauresControllerSensor(hass, controller, flat_id, sn,scan_interval)
        myControllers = list(map(create_myController, sns))

        if myControllers: async_add_entities(myControllers, True)
        
class SauresSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, controller, flat_id, serial_number,is_debug,scan_interval):
        """Initialize the sensor."""

        self.controller = controller
        self.flat_id = flat_id
        self.serial_number = str(serial_number)
        self.isStart = True
        self.isDebug = is_debug
        self._attributes = dict()

        self.set_scan_interval(hass, scan_interval)

    def set_scan_interval(self,hass, scan_interval):
        """Update scan interval."""
        def refresh(event_time):
            """Get the latest data from Transmission."""
            self.async_update()
        if self.isDebug:
            _LOGGER.warning("scan_interval=" + str(scan_interval))

        async_track_time_interval(
            hass, refresh, scan_interval
        )


    @property
    def current_meter(self):
        return self.controller.get_meter(self.flat_id, self.serial_number)

    @property
    def entity_id(self):
        """Return the entity_id of the sensor."""
        sn = self.serial_number.replace('-', '_')
        reg = re.compile('[^a-zA-Z0-9]')
        sn = reg.sub('', sn).lower()
        return f'sensor.sauresha_{self.flat_id}_{sn}'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        return 'mdi:counter'

    @property
    def device_state_attributes(self):
        return self._attributes

    async def async_fetch_state(self):
        """Retrieve latest state."""
        if self.isDebug:
            _LOGGER.warning("Update Start")
            
        self.controller.re_auth()
        meter = self.current_meter
        if meter.type_number==8:
            self._attributes.update({
                'friendly_name': meter.name,
                'condition': meter.state,
                'sn': meter.sn,
                'type': meter.type,
                'meter_id': meter.id,
                'input': meter.input,
                'approve_dt': meter.approve_dt,
                't1': meter.t1,
                't2': meter.t2,
                't3': meter.t3,
                't4': meter.t4
            })
        else:
            self._attributes.update({
                'friendly_name': meter.name,
                'condition': meter.state,
                'sn': meter.sn,
                'type': meter.type,
                'meter_id': meter.id,
                'input': meter.input,
                'approve_dt': meter.approve_dt,
            })
        if self.isStart:
            if meter.type_number == 1 or meter.type_number == 2 or meter.type_number == 3:
                self._attributes.update({
                    'unit_of_measurement': 'м³'}) 
            elif meter.type_number == 5:
                self._attributes.update({
                    'unit_of_measurement': '°C'})
            elif meter.type_number == 8:
                self._attributes.update({
                    'unit_of_measurement': 'кВт·ч'})
                    
            self.isStart = False
        return meter.value
        
    async def async_update(self):
        self._state = await self.async_fetch_state()

class SauresControllerSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, controller, flat_id, serial_number,scan_interval=SCAN_INTERVAL):
        """Initialize the sensor."""
        self.controller = controller
        self.flat_id = flat_id
        self.serial_number = str(serial_number)
        self._attributes = dict()

    @property
    def current_controllerInfo(self):
        return self.controller.get_controller(self.flat_id, self.serial_number)

    @property
    def entity_id(self):
        """Return the entity_id of the sensor."""
        sn = self.serial_number.replace('-', '_')
        reg = re.compile('[^a-zA-Z0-9]')
        sn = reg.sub('', sn).lower()
        return f'sensor.sauresha_contr_{sn}'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        return 'mdi:xbox-controller-view'

    @property
    def device_state_attributes(self):
        return self._attributes

    async def async_fetch_state(self):
        """Retrieve latest state."""
        self.controller.re_auth()
        myController = self.current_controllerInfo
        self._attributes.update({
            'battery_level': myController.batery,
            'condition': myController.state,
            'sn': myController.sn,
            'local_ip': myController.local_ip,
            'last_connection': myController.last_connection,
            'firmware':  myController.firmware,
            'ssid':  myController.ssid,
            'readout_dt':  myController.readout_dt,
            'request_dt':  myController.request_dt,
            'rssi':  myController.rssi,
            'hardware':  myController.hardware,
            'new_firmware':  myController.new_firmware,
            'last_connection':  myController.last_connection,
            'last_connection_warning':  myController.last_connection_warning,
            'check_hours':  myController.check_hours,
            'check_period_display':  myController.check_period_display,
            'requests':  myController.requests,
            'log':  myController.log,
            'cap_state':  myController.cap_state,
            'power_supply':  myController.power_supply
        })
        return myController.state
        
    async def async_update(self):
        self._state = await self.async_fetch_state()
