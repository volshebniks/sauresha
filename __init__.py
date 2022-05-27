"""Support for Saures Connect appliances."""

import asyncio
import logging
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry


from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL

from .const import (
    DOMAIN,
    CONF_DEBUG,
    CONF_FLATS,
    CONF_ISDEBUG,
    STARTUP_MESSAGE,
    PLATFORMS,
    COORDINATOR,
)
from .api import SauresHA

_LOGGER = logging.getLogger(__name__)


def setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up component."""
    # Print startup messages
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info(STARTUP_MESSAGE)
    # Clean up old imports from configuration.yaml
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == SOURCE_IMPORT:
            hass.config_entries.remove(entry.entry_id)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    cur_config = config_entry.data
    cur_options = config_entry.options
    SauresAPI: SauresHA = SauresHA(
        hass,
        cur_config.get(CONF_EMAIL),
        cur_config.get(CONF_PASSWORD),
        CONF_ISDEBUG,
        cur_options.get(CONF_FLATS),
    )
    await SauresAPI.async_fetch_data()

    hass.data[DOMAIN] = {
        CONF_SCAN_INTERVAL: cur_config.get(CONF_SCAN_INTERVAL),
        CONF_DEBUG: CONF_ISDEBUG,
        COORDINATOR: SauresAPI,
    }
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)
    return True


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    return True
