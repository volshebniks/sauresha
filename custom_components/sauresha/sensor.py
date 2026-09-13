"""Платформа sensor для SauresHA."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import SauresDataUpdateCoordinator
from .entity import SauresControllerSensor, SauresSensor, SauresTariffSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Настроить платформу sensor: контроллеры и счётчики."""
    coordinator: SauresDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        COORDINATOR
    ]
    api = coordinator.api
    entities: list = []

    for curflat in api.flats:
        try:
            controllers = await api.async_get_controllers(curflat)
            for obj in controllers:
                sn = obj.get("sn")
                if not sn:
                    continue
                entities.append(
                    SauresControllerSensor(
                        coordinator,
                        curflat,
                        sn,
                        obj.get("name"),
                        controller_hardware=obj.get("hardware"),
                        controller_firmware=obj.get("firmware"),
                    )
                )

            sensors = await api.async_get_sensors(curflat)
            for cur_sensor in sensors:
                try:
                    controller_sn = cur_sensor.get("controller_sn")
                    if not controller_sn:
                        continue
                    values = cur_sensor.get("vals") or []
                    type_number = cur_sensor.get("type", {}).get("number")
                    meter_kwargs = {
                        "controller_sn": controller_sn,
                        "controller_name": cur_sensor.get("controller_name"),
                        "controller_hardware": cur_sensor.get("controller_hardware"),
                        "controller_firmware": cur_sensor.get("controller_firmware"),
                    }
                    entities.append(
                        SauresSensor(
                            coordinator,
                            curflat,
                            cur_sensor.get("meter_id"),
                            cur_sensor.get("sn"),
                            cur_sensor.get("meter_name"),
                            type_number,
                            len(values),
                            **meter_kwargs,
                        )
                    )
                    # Многотарифная электроэнергия — отдельные числовые сенсоры T1..Tn
                    if type_number == 8 and len(values) > 1:
                        for tariff_index in range(1, len(values) + 1):
                            entities.append(
                                SauresTariffSensor(
                                    coordinator,
                                    curflat,
                                    cur_sensor.get("meter_id"),
                                    cur_sensor.get("sn"),
                                    cur_sensor.get("meter_name"),
                                    tariff_index,
                                    **meter_kwargs,
                                )
                            )
                except Exception:
                    _LOGGER.exception(
                        "Error setting up meter %s for flat %s",
                        cur_sensor.get("meter_id"),
                        curflat,
                    )
        except Exception:
            _LOGGER.exception("Error setting up sensors for flat %s", curflat)

    if entities:
        async_add_entities(entities)
