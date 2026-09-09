"""DataUpdateCoordinator for SauresHA."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SauresHA
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SauresDataUpdateCoordinator(DataUpdateCoordinator[bool]):
    """Coordinator to poll Saures cloud API once for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: SauresHA,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=update_interval,
        )
        self.api = api

    async def _async_update_data(self) -> bool:
        """Fetch data from Saures API."""
        try:
            await self.api.async_fetch_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Saures API: {err}") from err
        return True
