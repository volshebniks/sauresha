#  Copyright (c) 2020-2026, Sergey Golynskiy <master@g-s-a.me>
#  Creative Commons BY-NC-SA 4.0 International Public License
#  (see LICENSE.md or https://creativecommons.org/licenses/by-nc-sa/4.0/)
"""Константы интеграции SauresHA."""

from homeassistant.const import Platform

NAME = "Saures"
DOMAIN = "sauresha"
VERSION = "2.1.0"
ATTRIBUTION = "Home assistant component for Saures"
ISSUE_URL = "https://github.com/volshebniks/sauresha/issues"

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have ANY issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Configuration and options
CONF_ISDEBUG = False
CONF_DEBUG = "debug"
CONF_FLATS = "flats"
CONF_FLAT_ID = "flat_id"
CONF_SENSORS = "sensors"
# On Saures API [9 = Датчик] [10 = Состояние крана]
CONF_BINARY_SENSORS_DEF = [9, 10]
CONF_BINARY_SENSOR_DEV_CLASS_MOISTURE_DEF = [9]
CONF_BINARY_SENSOR_DEV_CLASS_OPENING_DEF = [10]
CONF_SWITCH_DEF = [6]

COORDINATOR = "coordinator"

# Command
CONF_COMMAND_ACTIVATE = "activate"
CONF_COMMAND_DEACTIVATE = "deactivate"

DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 5


def controller_device_identifier(flat_id, controller_sn: str) -> str:
    """Сформировать стабильный идентификатор устройства контроллера для реестра HA."""
    return f"{flat_id}_{controller_sn}"
