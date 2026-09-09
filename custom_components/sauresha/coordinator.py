"""Координатор обновления данных SauresHA."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SauresHA
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Небольшая пауза между объектами на фоновых обновлениях (не при первом старте).
BACKGROUND_FLAT_DELAY = 2.0


class SauresDataUpdateCoordinator(DataUpdateCoordinator[bool]):
    """Координатор: один опрос облачного API Saures для всех сущностей."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api: SauresHA,
        update_interval: timedelta,
    ) -> None:
        """Инициализировать координатор обновления."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=update_interval,
        )
        self.api = api
        self._first_refresh_done = False

    async def _async_update_data(self) -> bool:
        """Запросить актуальные данные у API Saures."""
        # Первый refresh без пауз — иначе setup entry отменяется (CancelledError).
        delay = 0.0 if not self._first_refresh_done else BACKGROUND_FLAT_DELAY
        try:
            await self.api.async_fetch_data(delay_between_flats=delay)
        except asyncio.CancelledError:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Saures API: {err}") from err
        self._first_refresh_done = True
        return True
