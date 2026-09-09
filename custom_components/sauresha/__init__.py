"""Support for Saures Connect appliances."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api import SauresHA
from .const import (
    CONF_DEBUG,
    CONF_FLATS,
    CONF_ISDEBUG,
    COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)
from .coordinator import SauresDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the SauresHA component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info(STARTUP_MESSAGE)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SauresHA from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    flats = entry.options.get(CONF_FLATS, [])
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    if scan_interval < 5:
        scan_interval = DEFAULT_SCAN_INTERVAL

    api = SauresHA(
        hass,
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        CONF_ISDEBUG,
        flats,
    )

    coordinator = SauresDataUpdateCoordinator(
        hass,
        entry,
        api,
        timedelta(minutes=scan_interval),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_SCAN_INTERVAL: scan_interval,
        CONF_DEBUG: CONF_ISDEBUG,
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    return True
