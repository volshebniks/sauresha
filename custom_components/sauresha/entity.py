import logging
import datetime
import re
import asyncio
from datetime import timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify

from .api import SauresHA
from .const import CONF_COMMAND_ACTIVATE, CONF_COMMAND_DEACTIVATE

_LOGGER = logging.getLogger(__name__)


class SauresSensor(Entity):
    """Representation of a Sensor."""

    _state: str

    def __init__(
        self,
        hass,
        controller,
        flat_id,
        meter_id,
        sn,
        counter_name,
        is_debug,
        scan_interval,
    ):
        """Initialize the sensor."""

        self.controller: SauresHA = controller
        self.flat_id = flat_id
        self.serial_number = str(sn)
        self.counter_name = counter_name
        self.isStart = True
        self.isDebug = is_debug
        self._attributes = dict()
        self._state = ""
        self.meter_id = meter_id
        self.scan_interval = scan_interval

        self._unique_id = slugify(f"sauresha_{flat_id}_{meter_id}")

        self.set_scan_interval(hass, timedelta(minutes=scan_interval))

    def set_scan_interval(self, hass: object, scan_interval: timedelta):
        """Update scan interval."""

        async def refresh(event_time):
            await self.async_update()

        if self.isDebug:
            _LOGGER.warning("Scan_interval = %s", str(scan_interval))

        async_track_time_interval(hass, refresh, scan_interval)

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return f"sauresha_{self.flat_id}_{self.meter_id}"

    @property
    def current_meter(self):
        return self.controller.get_sensor(self.flat_id, self.meter_id)

    @property
    def name(self):
        """Return the entity_id of the sensor."""
        if not self.counter_name:
            self.counter_name = ""
        return self.counter_name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        return "mdi:counter"

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_fetch_state(self):
        """Retrieve latest state."""
        str_return_value = "Unknown"

        if self.isDebug:
            _LOGGER.warning("Update Start meter_id: %s", str(self.meter_id))

        lock = asyncio.Lock()
        async with lock:
            await self.controller.async_fetch_data()

        meter = self.current_meter
        str_return_value = meter.value
        if meter.type_number == 8:
            self._attributes.update(
                {
                    "friendly_name": meter.name,
                    "condition": meter.state,
                    "sn": meter.sn,
                    "type": meter.type,
                    "meter_id": meter.meter_id,
                    "input": meter.input,
                    "approve_dt": meter.approve_dt,
                    "t1": meter.t1,
                    "t2": meter.t2,
                    "t3": meter.t3,
                    "t4": meter.t4,
                }
            )
        else:
            self._attributes.update(
                {
                    "friendly_name": meter.name,
                    "condition": meter.state,
                    "sn": meter.sn,
                    "type": meter.type,
                    "meter_id": meter.meter_id,
                    "input": meter.input,
                    "approve_dt": meter.approve_dt,
                }
            )
        if self.isStart:
            if meter.type_number == 1 or meter.type_number == 2:
                self._attributes.update(
                    {"unit_of_measurement": "m³", "state_class": "total_increasing"}
                )
            elif meter.type_number == 3:
                self._attributes.update(
                    {
                        "unit_of_measurement": "m³",
                        "device_class": "gas",
                        "state_class": "total_increasing",
                    }
                )
            elif meter.type_number == 5:
                self._attributes.update({"unit_of_measurement": "°C"})
            elif meter.type_number == 8:
                self._attributes.update(
                    {
                        "unit_of_measurement": "kWh",
                        "device_class": "energy",
                        "state_class": "total_increasing",
                    }
                )

            self.isStart = False

        self._attributes.update({"last_update_time": datetime.datetime.now()})

        self._attributes.update(
            {
                "next_update_time": datetime.datetime.now()
                + timedelta(minutes=self.scan_interval)
            }
        )
        if self.isDebug:
            _LOGGER.warning("Update Finish meter_id: %s", str(self.meter_id))

        return str_return_value

    async def async_update(self):
        self._state = await self.async_fetch_state()


class SauresBinarySensor(Entity):
    """Representation of a BinarySensor."""

    def __init__(
        self,
        hass,
        controller,
        flat_id,
        meter_id,
        serial_number,
        counter_name,
        is_debug,
        scan_interval,
    ):
        """Initialize the sensor."""

        self.controller: SauresHA = controller
        self.flat_id = flat_id
        self.meter_id = meter_id
        self.serial_number = serial_number
        self.counter_name = counter_name
        self._attributes = dict()
        self.isDebug = is_debug
        self._state = False
        self.scan_interval = scan_interval

        self._unique_id = slugify(f"sauresha_{flat_id}_{meter_id}")
        self.set_scan_interval(hass, timedelta(minutes=self.scan_interval))

    def set_scan_interval(self, hass: object, scan_interval: timedelta):
        """Update scan interval."""

        async def refresh(event_time):
            await self.async_update()

        if self.isDebug:
            _LOGGER.warning("Scan_interval = %s", str(scan_interval))

        async_track_time_interval(hass, refresh, scan_interval)

    @property
    def current_sensor(self):
        return self.controller.get_binarysensor(self.flat_id, self.meter_id)

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return self._unique_id

    @property
    def entity_id(self):
        """Return the entity_id of the sensor."""
        if not self.counter_name:
            self.counter_name = ""

        if len(self.counter_name) > 0:
            final_name = slugify(f"{self.counter_name}")
        elif len(self.serial_number) > 0:
            final_name = slugify(f"{self.flat_id}_{self.serial_number}")
        else:
            final_name = slugify(f"{self.flat_id}_{self.meter_id}")
        sn = final_name.replace("-", "_")
        reg = re.compile("[^a-zA-Z0-9_]")
        sn = reg.sub("", sn).lower()
        return f"binary_sensor.sauresha_{sn}"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return bool(int(self._state))

    @property
    def state(self):
        """Return the state of the sensor."""
        return bool(int(self._state))

    @property
    def available(self):
        """Return true if the binary sensor is available."""
        return self._state is not None

    @property
    def icon(self):
        return "mdi:alarm-check"

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_fetch_state(self):
        """Retrieve latest state."""
        if self.isDebug:
            _LOGGER.warning("Update Start meter_id: %s", str(self.meter_id))

        lock = asyncio.Lock()
        async with lock:
            await self.controller.async_fetch_data()

        meter = self.current_sensor
        return_value = meter.value
        self._attributes.update(
            {
                "friendly_name": meter.name,
                "condition": meter.state,
                "sn": meter.sn,
                "type": meter.type,
                "meter_id": meter.meter_id,
                "input": meter.input,
            }
        )
        if meter.state is not None:
            if meter.state.upper() == "ОБРЫВ":
                return_value = True
        else:
            _LOGGER.error("API ERROR during Auth process")

        self._attributes.update({"last_update_time": datetime.datetime.now()})

        self._attributes.update(
            {
                "next_update_time": datetime.datetime.now()
                + timedelta(minutes=self.scan_interval)
            }
        )
        if self.isDebug:
            _LOGGER.warning("Update Finish meter_id: %s", str(self.meter_id))

        return return_value

    async def async_update(self):
        self._state = await self.async_fetch_state()


class SauresControllerSensor(Entity):
    """Representation of a Sensor."""

    _state: str

    def __init__(
        self,
        hass,
        controller,
        flat_id,
        sn,
        counter_name,
        is_debug,
        scan_interval,
    ):
        """Initialize the sensor."""
        self.controller: SauresHA = controller
        self.flat_id = flat_id
        self.serial_number = str(sn)
        self.counter_name = str(counter_name)
        self._state = ""
        self.isDebug = is_debug
        self._attributes = dict()
        self.scan_interval = scan_interval

        self._unique_id = slugify(f"sauresha_{flat_id}_{sn}")

    @property
    def current_controller_info(self):
        return self.controller.get_controller(self.flat_id, self.serial_number)

    @property
    def unique_id(self):
        """Return the entity_id of the sensor."""
        return f"sauresha_contr_{self.flat_id}_{self.serial_number}"

    @property
    def name(self):
        """Return the entity_id of the sensor."""
        if not self.counter_name:
            self.counter_name = ""
        return self.counter_name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        return "mdi:xbox-controller-view"

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_set_scan_interval(self, hass: object, scan_interval: timedelta):
        """Update scan interval."""

        async def refresh(event_time):
            await self.async_update()

        if self.isDebug:
            _LOGGER.warning("Scan_interval = %s", str(scan_interval))

        async_track_time_interval(hass, refresh, timedelta(minutes=scan_interval))

    async def async_fetch_state(self):
        """Retrieve latest state."""
        str_return_value = "Unknown"
        if self.isDebug:
            _LOGGER.warning("Update Start sn: %s", str(self.serial_number))

        lock = asyncio.Lock()
        async with lock:
            await self.controller.async_fetch_data()

        my_controller = self.current_controller_info
        str_return_value = my_controller.state
        self._attributes.update(
            {
                "friendly_name": self.counter_name,
                "battery_level": my_controller.battery,
                "condition": my_controller.state,
                "sn": my_controller.sn,
                "local_ip": my_controller.local_ip,
                "firmware": my_controller.firmware,
                "ssid": my_controller.ssid,
                "readout_dt": my_controller.readout_dt,
                "request_dt": my_controller.request_dt,
                "rssi": my_controller.rssi,
                "hardware": my_controller.hardware,
                "new_firmware": my_controller.new_firmware,
                "last_connection": my_controller.last_connection,
                "last_connection_warning": my_controller.last_connection_warning,
                "check_hours": my_controller.check_hours,
                "check_period_display": my_controller.check_period_display,
                "requests": my_controller.requests,
                "log": my_controller.log,
                "cap_state": my_controller.cap_state,
                "power_supply": my_controller.power_supply,
            }
        )
        self._attributes.update({"last_update_time": datetime.datetime.now()})

        self._attributes.update(
            {
                "next_update_time": datetime.datetime.now()
                + timedelta(minutes=self.scan_interval)
            }
        )
        if self.isDebug:
            _LOGGER.warning("Update Finish sn: %s", str(self.serial_number))
        return str_return_value

    async def async_update(self):
        self._state = await self.async_fetch_state()


class SauresSwitch(SwitchEntity):
    """Representation of a Switch."""

    _state: str

    def __init__(
        self,
        hass,
        controller,
        flat_id,
        meter_id,
        sn,
        counter_name,
        is_debug,
        scan_interval,
    ):
        """Initialize the switch."""

        self.controller: SauresHA = controller
        self.flat_id = flat_id
        self.serial_number = str(sn)
        self.counter_name = counter_name
        self.isStart = True
        self.isDebug = is_debug
        self._attributes = dict()
        self._state = ""
        self.meter_id = meter_id
        self.scan_interval = scan_interval

        self._unique_id = slugify(f"sauresha_{flat_id}_{meter_id}")
        self.set_scan_interval(hass, timedelta(minutes=scan_interval))

    def set_scan_interval(self, hass: object, scan_interval: timedelta):
        """Update scan interval."""

        async def refresh(event_time):
            await self.async_update()

        if self.isDebug:
            _LOGGER.warning("Scan_interval = %s", str(scan_interval))

        async_track_time_interval(hass, refresh, scan_interval)

    @property
    def current_meter(self):
        return self.controller.get_switch(self.flat_id, self.meter_id)

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return self._unique_id

    @property
    def entity_id(self):
        """Return the entity_id of the sensor."""
        if not self.counter_name:
            self.counter_name = ""

        if len(self.counter_name) > 0:
            final_name = slugify(f"{self.counter_name}")
        elif len(self.serial_number) > 0:
            final_name = slugify(f"{self.flat_id}_{self.serial_number}")
        else:
            final_name = slugify(f"{self.flat_id}_{self.meter_id}")

        sn = final_name.replace("-", "_")
        reg = re.compile("[^a-zA-Z0-9_]")
        sn = reg.sub("", sn).lower()
        return f"switch.sauresha_{sn}"

    def turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        if self.controller.set_command(self.meter_id, CONF_COMMAND_ACTIVATE):
            self.controller.get_switches(self.flat_id, True)

    def turn_off(self, **kwargs) -> None:
        """Turn the entity on."""
        if self.controller.set_command(self.meter_id, CONF_COMMAND_DEACTIVATE):
            self.controller.get_switches(self.flat_id, True)

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return bool(int(self._state))

    @property
    def icon(self):
        return "mdi:switch"

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_fetch_state(self):
        """Retrieve latest state."""
        str_return_value = "Unknown"

        if self.isDebug:
            _LOGGER.warning("Update Start meter_id: %s", str(self.meter_id))

        lock = asyncio.Lock()
        async with lock:
            await self.controller.async_fetch_data()

        meter = self.current_meter
        str_return_value = meter.value
        if meter.type_number == 8:
            self._attributes.update(
                {
                    "friendly_name": meter.name,
                    "condition": meter.state,
                    "sn": meter.sn,
                    "type": meter.type,
                    "meter_id": meter.meter_id,
                    "input": meter.input,
                    "approve_dt": meter.approve_dt,
                    "t1": meter.t1,
                    "t2": meter.t2,
                    "t3": meter.t3,
                    "t4": meter.t4,
                }
            )
        else:
            self._attributes.update(
                {
                    "friendly_name": meter.name,
                    "condition": meter.state,
                    "sn": meter.sn,
                    "type": meter.type,
                    "meter_id": meter.meter_id,
                    "input": meter.input,
                    "approve_dt": meter.approve_dt,
                }
            )
        if self.isStart:
            if meter.type_number == 1 or meter.type_number == 2:
                self._attributes.update(
                    {"unit_of_measurement": "m³", "state_class": "total_increasing"}
                )
            elif meter.type_number == 3:
                self._attributes.update(
                    {
                        "unit_of_measurement": "m³",
                        "device_class": "gas",
                        "state_class": "total_increasing",
                    }
                )
            elif meter.type_number == 5:
                self._attributes.update({"unit_of_measurement": "°C"})
            elif meter.type_number == 8:
                self._attributes.update(
                    {
                        "unit_of_measurement": "kWh",
                        "device_class": "energy",
                        "state_class": "total_increasing",
                    }
                )

            self.isStart = False

        self._attributes.update({"last_update_time": datetime.datetime.now()})

        self._attributes.update(
            {
                "next_update_time": datetime.datetime.now()
                + timedelta(minutes=self.scan_interval)
            }
        )
        if self.isDebug:
            _LOGGER.warning("Update Finish meter_id: %s", str(self.meter_id))
        return str_return_value

    async def async_update(self):
        self._state = await self.async_fetch_state()
