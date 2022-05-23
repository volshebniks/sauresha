"""Support for Saures Connect appliances."""

import asyncio
import logging
import voluptuous as vol

from datetime import timedelta
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry


from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from .const import (
    DOMAIN,
    CONF_DEBUG,
    CONF_FLATS,
    STARTUP_MESSAGE,
    PLATFORMS,
    COORDINATOR,
)
from .api import SauresHA

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_EMAIL): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): vol.All(
                    cv.time_period, cv.positive_timedelta
                ),
                vol.Optional(CONF_DEBUG, default=False): cv.boolean,
                vol.Optional(CONF_FLATS, default=""): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up component."""
    # Print startup messages
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info(STARTUP_MESSAGE)
    # Clean up old imports from configuration.yaml
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source == SOURCE_IMPORT:
            hass.config_entries.remove(entry.entry_id)

    if DOMAIN not in config:
        return True

    SauresAPI: SauresHA = SauresHA(
        hass,
        config[DOMAIN].get(CONF_EMAIL),
        config[DOMAIN].get(CONF_PASSWORD),
        config[DOMAIN].get(CONF_DEBUG),
        config[DOMAIN].get(CONF_FLATS),
    )
    SauresAPI.fetch_data()

    hass.data[DOMAIN] = {
        CONF_SCAN_INTERVAL: config[DOMAIN].get(CONF_SCAN_INTERVAL),
        CONF_DEBUG: config[DOMAIN].get(CONF_DEBUG),
        COORDINATOR: SauresAPI,
    }

    for component in PLATFORMS:
        hass.helpers.discovery.load_platform(component, DOMAIN, {}, config)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    cur_config = config_entry.data
    cur_options = config_entry.options
    SauresAPI: SauresHA = SauresHA(
        hass,
        cur_config.get(CONF_EMAIL),
        cur_config.get(CONF_PASSWORD),
        False,
        cur_options.get(CONF_FLATS),
    )
    await SauresAPI.async_fetch_data()

    hass.data[DOMAIN] = {
        CONF_SCAN_INTERVAL: cur_config.get(CONF_SCAN_INTERVAL),
        CONF_DEBUG: False,
        COORDINATOR: SauresAPI,
    }
    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)
    return True


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    return True
