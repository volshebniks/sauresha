"""Платформа binary_sensor для SauresHA."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_OVERCONSUMPTION_METER_TYPES, COORDINATOR, DOMAIN
from .coordinator import SauresDataUpdateCoordinator
from .entity import SauresBinarySensor, SauresSuspiciousConsumptionBinarySensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настроить binary_sensor: протечки, контакты и подозрительный расход."""
    coordinator: SauresDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        COORDINATOR
    ]
    api = coordinator.api
    entities: list = []

    for curflat in api.flats:
        try:
            sensors = await api.async_get_binary_sensors(curflat)
            for cur_sensor in sensors:
                try:
                    controller_sn = cur_sensor.get("controller_sn")
                    if not controller_sn:
                        continue
                    entities.append(
                        SauresBinarySensor(
                            coordinator,
                            curflat,
                            cur_sensor.get("type", {}).get("number"),
                            cur_sensor.get("meter_id"),
                            cur_sensor.get("sn"),
                            cur_sensor.get("meter_name"),
                            controller_sn=controller_sn,
                            controller_name=cur_sensor.get("controller_name"),
                            controller_hardware=cur_sensor.get("controller_hardware"),
                            controller_firmware=cur_sensor.get("controller_firmware"),
                        )
                    )
                except Exception:
                    _LOGGER.exception(
                        "Error setting up binary meter %s for flat %s",
                        cur_sensor.get("meter_id"),
                        curflat,
                    )

            # Подозрительный расход — по счётчикам воды/газа (state.number == 3)
            meters = await api.async_get_sensors(curflat)
            for cur_sensor in meters:
                try:
                    type_number = cur_sensor.get("type", {}).get("number")
                    if type_number not in CONF_OVERCONSUMPTION_METER_TYPES:
                        continue
                    controller_sn = cur_sensor.get("controller_sn")
                    if not controller_sn:
                        continue
                    entities.append(
                        SauresSuspiciousConsumptionBinarySensor(
                            coordinator,
                            curflat,
                            cur_sensor.get("meter_id"),
                            cur_sensor.get("sn"),
                            cur_sensor.get("meter_name"),
                            controller_sn=controller_sn,
                            controller_name=cur_sensor.get("controller_name"),
                            controller_hardware=cur_sensor.get("controller_hardware"),
                            controller_firmware=cur_sensor.get("controller_firmware"),
                        )
                    )
                except Exception:
                    _LOGGER.exception(
                        "Error setting up overconsumption sensor %s for flat %s",
                        cur_sensor.get("meter_id"),
                        curflat,
                    )
        except Exception:
            _LOGGER.exception("Error setting up binary sensors for flat %s", curflat)

    if entities:
        async_add_entities(entities)
