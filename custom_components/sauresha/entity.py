"""Классы сущностей Home Assistant для SauresHA."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    UnitOfEnergy,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_BINARY_SENSOR_DEV_CLASS_MOISTURE_DEF,
    CONF_BINARY_SENSOR_DEV_CLASS_OPENING_DEF,
    CONF_COMMAND_ACTIVATE,
    CONF_COMMAND_DEACTIVATE,
    DOMAIN,
    EVENT_SUSPICIOUS_CONSUMPTION,
    STATE_OVERCONSUMPTION,
    controller_device_identifier,
)
from .coordinator import SauresDataUpdateCoordinator


def _parse_bool_state(value: Any) -> bool:
    """Преобразовать значение API к логическому типу."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip()
    if text.isdigit():
        return bool(int(text))
    return text.lower() in ("true", "on", "1", "yes")


class SauresEntity(CoordinatorEntity[SauresDataUpdateCoordinator]):
    """Базовая сущность интеграции SauresHA."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: SauresDataUpdateCoordinator,
        flat_id: Any,
        unique_suffix: str,
        name: str,
        *,
        controller_sn: str,
        serial_number: str | None = None,
        controller_name: str | None = None,
        controller_hardware: str | None = None,
        controller_firmware: str | None = None,
    ) -> None:
        """Инициализировать базовую сущность и привязку к устройству контроллера."""
        super().__init__(coordinator)
        self.flat_id = flat_id
        self.controller_sn = str(controller_sn)
        self.serial_number = str(serial_number or "")
        self._controller_name = controller_name
        self._controller_hardware = controller_hardware
        self._controller_firmware = controller_firmware
        self._attr_unique_id = f"sauresha_{flat_id}_{unique_suffix}"
        self._attr_name = name if name else f"[SAURES] [{flat_id}] [{unique_suffix}]"
        self._attr_device_info = self._build_device_info()

    @property
    def api(self):
        """Вернуть клиент API из координатора."""
        return self.coordinator.api

    def _build_device_info(self) -> DeviceInfo:
        """Собрать DeviceInfo для группировки сущностей под контроллером."""
        device_id = controller_device_identifier(self.flat_id, self.controller_sn)
        controller = self.api.get_controller(self.flat_id, self.controller_sn)

        name = (
            self._controller_name
            or controller.name
            or f"Saures {self.controller_sn}"
        )
        hardware = self._controller_hardware or controller.hardware
        firmware = self._controller_firmware or controller.firmware

        return DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"[SAURES] {name}",
            manufacturer="SAURES",
            model=self.api.get_controller_name(hardware),
            sw_version=firmware,
            serial_number=self.controller_sn,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Обновить атрибуты сущности после опроса координатора."""
        self._update_from_coordinator()
        super()._handle_coordinator_update()

    def _update_from_coordinator(self) -> None:
        """Заполнить _attr_* из кэша API. Переопределяется в наследниках."""
        return


class SauresSensor(SauresEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Сенсор показаний счётчика Saures."""

    def __init__(
        self,
        coordinator: SauresDataUpdateCoordinator,
        flat_id: Any,
        meter_id: Any,
        sn: str,
        counter_name: str,
        type_number: int | None = None,
        values_count: int = 0,
        *,
        controller_sn: str,
        controller_name: str | None = None,
        controller_hardware: str | None = None,
        controller_firmware: str | None = None,
    ) -> None:
        """Инициализировать сенсор счётчика."""
        display_name = (
            f"[SAURES] {counter_name}"
            if counter_name
            else f"[SAURES] [{flat_id}] [{meter_id}]"
        )
        super().__init__(
            coordinator,
            flat_id,
            str(meter_id),
            display_name,
            controller_sn=controller_sn,
            serial_number=sn,
            controller_name=controller_name,
            controller_hardware=controller_hardware,
            controller_firmware=controller_firmware,
        )
        self.meter_id = meter_id
        self._attr_icon = "mdi:counter"
        self._expects_numeric = False
        self._type_number = self._coerce_type_number(type_number)
        self._apply_type(self._type_number, values_count)
        self._update_from_coordinator()

    @staticmethod
    def _coerce_type_number(type_number: Any) -> int | None:
        """Привести номер типа API к int (API иногда отдаёт строку)."""
        if type_number is None:
            return None
        try:
            return int(type_number)
        except (TypeError, ValueError):
            return None

    def _apply_type(self, type_number: int | None, values_count: int = 0) -> None:
        """Задать device_class и единицы измерения по типу счётчика Saures."""
        self._expects_numeric = False
        if type_number in (1, 2):
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
            self._attr_device_class = SensorDeviceClass.WATER
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._expects_numeric = True
        elif type_number == 3:
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
            self._attr_device_class = SensorDeviceClass.GAS
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._expects_numeric = True
        elif type_number == 5:
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._expects_numeric = True
        elif type_number == 8:
            # Многотарифные счётчики отдают строку "t1/t2/..." — без unit/device_class.
            # Числовые тарифы создаются отдельными сущностями.
            if values_count <= 1:
                self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
                self._attr_device_class = SensorDeviceClass.ENERGY
                self._attr_state_class = SensorStateClass.TOTAL_INCREASING
                self._expects_numeric = True
            else:
                self._attr_native_unit_of_measurement = None
                self._attr_device_class = None
                self._attr_state_class = None
        elif type_number == 11:
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._expects_numeric = True
        elif type_number == 13:
            self._attr_native_unit_of_measurement = UnitOfEnergy.GIGA_CALORIE
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
            self._expects_numeric = True
        elif type_number == 14:
            # Давление (скважина и т.п.), единица API — бар
            self._attr_native_unit_of_measurement = UnitOfPressure.BAR
            self._attr_device_class = SensorDeviceClass.PRESSURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._expects_numeric = True

    def _update_from_coordinator(self) -> None:
        """Обновить значение и атрибуты счётчика из кэша API."""
        meter = self.api.get_sensor(self.flat_id, self.meter_id)
        type_number = self._coerce_type_number(meter.type_number)
        if type_number is None:
            type_number = self._type_number
        else:
            self._type_number = type_number

        values_count = len(meter.values or [])
        # Повторно применяем тип: unit/device_class не должны сбрасываться
        # из‑за склейки vals или позднего появления type в ответе API.
        self._apply_type(type_number, values_count)

        value = meter.value
        # Комбинированная строка тарифов — только для электроэнергии (тип 8)
        if (
            type_number == 8
            and isinstance(value, str)
            and "/" in value
        ):
            self._attr_native_unit_of_measurement = None
            self._attr_device_class = None
            self._attr_state_class = None
            self._expects_numeric = False
        elif self._expects_numeric and value is not None:
            try:
                value = float(value)
            except (TypeError, ValueError):
                pass
        self._attr_native_value = value
        attrs: dict[str, Any] = {
            "condition": meter.state,
            "condition_number": meter.state_number,
            "sn": meter.sn,
            "type": meter.type,
            "meter_id": meter.meter_id,
            "input": meter.input,
            "approve_dt": meter.approve_dt,
            "controller_sn": self.controller_sn,
            "suspicious_consumption": meter.state_number == STATE_OVERCONSUMPTION,
        }
        if type_number == 8:
            attrs.update(
                {
                    "t1": meter.t1,
                    "t2": meter.t2,
                    "t3": meter.t3,
                    "t4": meter.t4,
                }
            )
        self._attr_extra_state_attributes = attrs


class SauresTariffSensor(SauresEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Числовой сенсор отдельного тарифа электросчётчика Saures."""

    def __init__(
        self,
        coordinator: SauresDataUpdateCoordinator,
        flat_id: Any,
        meter_id: Any,
        sn: str,
        counter_name: str,
        tariff_index: int,
        *,
        controller_sn: str,
        controller_name: str | None = None,
        controller_hardware: str | None = None,
        controller_firmware: str | None = None,
    ) -> None:
        """Инициализировать сенсор тарифа T1..T4."""
        base_name = counter_name or f"[{flat_id}] [{meter_id}]"
        display_name = f"[SAURES] {base_name} T{tariff_index}"
        super().__init__(
            coordinator,
            flat_id,
            f"{meter_id}_t{tariff_index}",
            display_name,
            controller_sn=controller_sn,
            serial_number=sn,
            controller_name=controller_name,
            controller_hardware=controller_hardware,
            controller_firmware=controller_firmware,
        )
        self.meter_id = meter_id
        self.tariff_index = tariff_index
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        """Обновить показание выбранного тарифа из кэша API."""
        meter = self.api.get_sensor(self.flat_id, self.meter_id)
        values = meter.values or []
        value: Any = None
        if 0 < self.tariff_index <= len(values):
            value = values[self.tariff_index - 1]
        try:
            value = float(value) if value is not None and value != "-" else None
        except (TypeError, ValueError):
            value = None
        self._attr_native_value = value
        self._attr_extra_state_attributes = {
            "condition": meter.state,
            "condition_number": meter.state_number,
            "sn": meter.sn,
            "type": meter.type,
            "meter_id": meter.meter_id,
            "input": meter.input,
            "tariff": f"T{self.tariff_index}",
            "controller_sn": self.controller_sn,
        }


class SauresBinarySensor(SauresEntity, BinarySensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Бинарный датчик Saures (протечка, сухой контакт и т.п.)."""

    def __init__(
        self,
        coordinator: SauresDataUpdateCoordinator,
        flat_id: Any,
        object_type: int | None,
        meter_id: Any,
        serial_number: str,
        counter_name: str,
        *,
        controller_sn: str,
        controller_name: str | None = None,
        controller_hardware: str | None = None,
        controller_firmware: str | None = None,
    ) -> None:
        """Инициализировать бинарный датчик."""
        display_name = (
            f"[SAURES] {counter_name}"
            if counter_name
            else f"[SAURES] [{flat_id}] [{meter_id}]"
        )
        super().__init__(
            coordinator,
            flat_id,
            str(meter_id),
            display_name,
            controller_sn=controller_sn,
            serial_number=serial_number,
            controller_name=controller_name,
            controller_hardware=controller_hardware,
            controller_firmware=controller_firmware,
        )
        self.object_type = object_type
        self.meter_id = meter_id

        if object_type in CONF_BINARY_SENSOR_DEV_CLASS_MOISTURE_DEF:
            self._attr_device_class = BinarySensorDeviceClass.MOISTURE
        elif object_type in CONF_BINARY_SENSOR_DEV_CLASS_OPENING_DEF:
            self._attr_device_class = BinarySensorDeviceClass.OPENING
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        """Обновить состояние и атрибуты бинарного датчика из кэша API."""
        meter = self.api.get_binarysensor(self.flat_id, self.meter_id)
        value = meter.value
        if meter.state is not None and str(meter.state).upper() == "ОБРЫВ":
            value = True
        self._attr_is_on = _parse_bool_state(value)
        self._attr_extra_state_attributes = {
            "condition": meter.state,
            "condition_number": meter.state_number,
            "sn": meter.sn,
            "type": meter.type,
            "meter_id": meter.meter_id,
            "input": meter.input,
            "controller_sn": self.controller_sn,
        }


class SauresSuspiciousConsumptionBinarySensor(
    SauresEntity, BinarySensorEntity
):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Бинарный датчик «Подозрительный расход» (meter.state.number == 3)."""

    def __init__(
        self,
        coordinator: SauresDataUpdateCoordinator,
        flat_id: Any,
        meter_id: Any,
        serial_number: str,
        counter_name: str,
        *,
        controller_sn: str,
        controller_name: str | None = None,
        controller_hardware: str | None = None,
        controller_firmware: str | None = None,
    ) -> None:
        """Инициализировать датчик подозрительного расхода."""
        base = counter_name or f"[{flat_id}] [{meter_id}]"
        display_name = f"[SAURES] Подозрительный расход {base}"
        super().__init__(
            coordinator,
            flat_id,
            f"{meter_id}_overconsumption",
            display_name,
            controller_sn=controller_sn,
            serial_number=serial_number,
            controller_name=controller_name,
            controller_hardware=controller_hardware,
            controller_firmware=controller_firmware,
        )
        self.meter_id = meter_id
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:pipe-leak"
        self._was_on: bool | None = None
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        """Обновить флаг подозрительного расхода и при срабатывании послать событие."""
        meter = self.api.get_sensor(self.flat_id, self.meter_id)
        is_on = meter.state_number == STATE_OVERCONSUMPTION
        prev = self._was_on
        self._attr_is_on = is_on
        self._attr_extra_state_attributes = {
            "condition": meter.state,
            "condition_number": meter.state_number,
            "sn": meter.sn,
            "type": meter.type,
            "meter_id": meter.meter_id,
            "input": meter.input,
            "controller_sn": self.controller_sn,
            "meter_name": meter.name,
        }
        # Событие только при переходе в активное состояние (аналог push от Saures)
        if is_on and prev is False and self.hass is not None:
            self.hass.bus.async_fire(
                EVENT_SUSPICIOUS_CONSUMPTION,
                {
                    "flat_id": self.flat_id,
                    "controller_sn": self.controller_sn,
                    "meter_id": meter.meter_id,
                    "meter_name": meter.name,
                    "condition": meter.state,
                    "condition_number": meter.state_number,
                    "entity_id": self.entity_id,
                },
            )
        self._was_on = is_on


class SauresControllerSensor(SauresEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Сенсор состояния контроллера Saures."""

    def __init__(
        self,
        coordinator: SauresDataUpdateCoordinator,
        flat_id: Any,
        sn: str,
        counter_name: str,
        *,
        controller_hardware: str | None = None,
        controller_firmware: str | None = None,
    ) -> None:
        """Инициализировать сенсор контроллера."""
        display_name = (
            f"[SAURES] {counter_name}"
            if counter_name
            else f"[SAURES] [{flat_id}] [{sn}]"
        )
        super().__init__(
            coordinator,
            flat_id,
            f"contr_{sn}",
            display_name,
            controller_sn=sn,
            serial_number=sn,
            controller_name=counter_name,
            controller_hardware=controller_hardware,
            controller_firmware=controller_firmware,
        )
        self._attr_unique_id = f"sauresha_contr_{flat_id}_{sn}"
        self._attr_icon = "mdi:home-circle"
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        """Обновить состояние и атрибуты контроллера из кэша API."""
        my_controller = self.api.get_controller(self.flat_id, self.serial_number)
        suspicious = self.api.get_suspicious_consumption_meters(
            self.flat_id, self.serial_number
        )
        self._attr_native_value = my_controller.state
        self._attr_extra_state_attributes = {
            ATTR_BATTERY_LEVEL: my_controller.battery,
            "condition": my_controller.state,
            "sn": my_controller.sn,
            "local_ip": my_controller.local_ip,
            "firmware": my_controller.firmware,
            "ssid": my_controller.ssid,
            "readout_dt": my_controller.readout_dt,
            "request_dt": my_controller.request_dt,
            "rssi": my_controller.rssi,
            "hardware": my_controller.hardware,
            "hardware_name": self.api.get_controller_name(my_controller.hardware),
            "new_firmware": my_controller.new_firmware,
            "last_connection": my_controller.last_connection,
            "last_connection_warning": my_controller.last_connection_warning,
            "check_hours": my_controller.check_hours,
            "check_period_display": my_controller.check_period_display,
            "requests": my_controller.requests,
            "log": my_controller.log,
            "cap_state": my_controller.cap_state,
            "power_supply": my_controller.power_supply,
            "suspicious_consumption": bool(suspicious),
            "suspicious_consumption_meters": suspicious,
        }


class SauresSwitch(SauresEntity, SwitchEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Переключатель управления краном Saures."""

    def __init__(
        self,
        coordinator: SauresDataUpdateCoordinator,
        flat_id: Any,
        meter_id: Any,
        sn: str,
        counter_name: str,
        *,
        controller_sn: str,
        controller_name: str | None = None,
        controller_hardware: str | None = None,
        controller_firmware: str | None = None,
    ) -> None:
        """Инициализировать switch управления краном."""
        display_name = (
            f"[SAURES] {counter_name}"
            if counter_name
            else f"[SAURES] [{flat_id}] [{meter_id}]"
        )
        super().__init__(
            coordinator,
            flat_id,
            f"switch_{meter_id}",
            display_name,
            controller_sn=controller_sn,
            serial_number=sn,
            controller_name=controller_name,
            controller_hardware=controller_hardware,
            controller_firmware=controller_firmware,
        )
        self.meter_id = meter_id
        self._attr_unique_id = f"sauresha_switch_{flat_id}_{meter_id}"
        self._attr_icon = "mdi:pipe-valve"
        self._update_from_coordinator()

    def _update_from_coordinator(self) -> None:
        """Обновить состояние и атрибуты крана из кэша API."""
        meter = self.api.get_switch(self.flat_id, self.meter_id)
        self._attr_is_on = _parse_bool_state(meter.value)
        self._attr_extra_state_attributes = {
            "condition": meter.state,
            "condition_number": meter.state_number,
            "sn": meter.sn,
            "type": meter.type,
            "meter_id": meter.meter_id,
            "input": meter.input,
            "approve_dt": meter.approve_dt,
            "controller_sn": self.controller_sn,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Включить/активировать кран через API."""
        result = await self.api.set_command(self.meter_id, CONF_COMMAND_ACTIVATE)
        if result:
            await self.api.async_get_switches(self.flat_id, True)
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Выключить/деактивировать кран через API."""
        result = await self.api.set_command(self.meter_id, CONF_COMMAND_DEACTIVATE)
        if result:
            await self.api.async_get_switches(self.flat_id, True)
            await self.coordinator.async_request_refresh()
