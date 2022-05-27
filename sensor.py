"""Provides a sensor for Saures."""
import logging
from homeassistant.const import CONF_SCAN_INTERVAL
from datetime import timedelta
from .const import DOMAIN, COORDINATOR
from .api import SauresHA
from .entity import SauresControllerSensor, SauresSensor

SCAN_INTERVAL = timedelta(seconds=600)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup sensor platform."""
    my_sensors: list = []
    is_debug = True
    scan_interval = config_entry.data.get(CONF_SCAN_INTERVAL)

    controller: SauresHA = hass.data[DOMAIN].get(COORDINATOR)
    for curflat in controller.flats:
        try:
            controllers = await controller.async_get_controllers(curflat)
            for obj in controllers:
                if len(obj.get("sn")) > 0:
                    my_controller = SauresControllerSensor(
                        hass,
                        controller,
                        curflat,
                        obj.get("sn"),
                        obj.get("name"),
                        is_debug,
                        scan_interval,
                    )
                    my_sensors.append(my_controller)

                    sensors = await controller.async_get_sensors(curflat)
                    for curSensor in sensors:
                        sensor = SauresSensor(
                            hass,
                            controller,
                            curflat,
                            curSensor.get("meter_id"),
                            curSensor.get("sn"),
                            curSensor.get("meter_name"),
                            is_debug,
                            scan_interval,
                        )
                        my_sensors.append(sensor)
        except Exception:
            _LOGGER.exception(str(Exception))

    if my_sensors:
        async_add_entities(my_sensors, True)
