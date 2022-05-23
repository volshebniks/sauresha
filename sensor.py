"""Provides a sensor for Saures."""
from datetime import timedelta
import logging
from homeassistant.const import CONF_SCAN_INTERVAL

from .const import CONF_DEBUG, DOMAIN, COORDINATOR
from .api import SauresHA
from .entity import SauresControllerSensor, SauresSensor


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=10)


def setup_platform(
    hass, config, add_entities, discovery_info=None, scan_interval=SCAN_INTERVAL
):
    """Setup the sensor platform."""
    my_sensors: list = []
    scan_interval = hass.data[DOMAIN].get(CONF_SCAN_INTERVAL)
    if scan_interval:
        scan_interval = SCAN_INTERVAL

    is_debug: bool = hass.data[DOMAIN].get(CONF_DEBUG)
    if is_debug:
        _LOGGER.warning("Scan_interval = %s", str(scan_interval))

    controller: SauresHA = hass.data[DOMAIN].get(COORDINATOR)

    for curflat in controller.flats:
        controllers = controller.get_controllers(curflat)
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

        sensors = controller.get_sensors(curflat)
        for obj in sensors:
            sensor = SauresSensor(
                hass,
                controller,
                curflat,
                obj.get("meter_id"),
                obj.get("sn"),
                obj.get("name"),
                is_debug,
                scan_interval,
            )
            my_sensors.append(sensor)

    if my_sensors:
        add_entities(my_sensors, True)
