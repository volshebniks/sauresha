import logging
from homeassistant.const import CONF_SCAN_INTERVAL
from datetime import timedelta
from homeassistant.core import HomeAssistant

from .const import DOMAIN, COORDINATOR
from .api import SauresHA
from .entity import SauresBinarySensor


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=10)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Setup sensor platform."""
    my_sensors: list = []
    is_debug = True
    scan_interval = config_entry.data.get(CONF_SCAN_INTERVAL)

    controller: SauresHA = hass.data[DOMAIN].get(COORDINATOR)
    for curflat in controller.flats:
        try:
            sensors = await controller.async_get_binary_sensors(curflat)
            for curSensor in sensors:
                sensor = SauresBinarySensor(
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
