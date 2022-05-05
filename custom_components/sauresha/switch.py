import logging
from homeassistant.const import CONF_SCAN_INTERVAL

from datetime import timedelta
from .const import CONF_DEBUG, DOMAIN, COORDINATOR
from .api import SauresHA
from .entity import SauresSwitch


_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)


def setup_platform(
    hass, config, add_entities, discovery_info=None, scan_interval=SCAN_INTERVAL
):
    """Setup the sensor platform."""

    my_sensors: list = []
    scan_interval = hass.data[DOMAIN].get(CONF_SCAN_INTERVAL)
    is_debug: bool = hass.data[DOMAIN].get(CONF_DEBUG)
    if is_debug:
        _LOGGER.warning("Scan_interval = %s", str(scan_interval))

    controller: SauresHA = hass.data[DOMAIN].get(COORDINATOR)

    for curflat in controller.flats:
        sensors = controller.get_switches(curflat, False)
        for obj in sensors:
            sensor = SauresSwitch(
                hass,
                controller,
                curflat,
                obj.get("meter_id"),
                obj.get("sn"),
                obj.get("meter_name"),
                is_debug,
                scan_interval,
            )
            my_sensors.append(sensor)

        if my_sensors:
            add_entities(my_sensors, True)
