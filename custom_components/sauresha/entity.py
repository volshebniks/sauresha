"""Entity classes for SauresHA."""

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
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_BINARY_SENSOR_DEV_CLASS_MOISTURE_DEF,
    CONF_BINARY_SENSOR_DEV_CLASS_OPENING_DEF,
    CONF_COMMAND_ACTIVATE,
    CONF_COMMAND_DEACTIVATE,
    DOMAIN,
    controller_device_identifier,
)
from .coordinator import SauresDataUpdateCoordinator


def _parse_bool_state(value: Any) -> bool:
    """Convert API values to boolean."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    text = str(value).strip()
    if text.isdigit():
        return bool(int(text))
    return text.lower() in ("true", "on", "1", "yes")


class SauresEntity(CoordinatorEntity[SauresDataUpdateCoordinator]):
    """Base entity for SauresHA."""

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
        """Initialize the base entity."""
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
        """Return API client."""
        return self.coordinator.api

    def _build_device_info(self) -> DeviceInfo:
        """Return DeviceInfo so all meters are grouped under the controller."""
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


class SauresSensor(SauresEntity, SensorEntity):
    """Representation of a Saures meter sensor."""

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
        """Initialize the sensor."""
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
        self._apply_type(type_number, values_count)

    def _apply_type(self, type_number: int | None, values_count: int = 0) -> None:
        """Set device class / units from Saures meter type."""
        if type_number in (1, 2):
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
            self._attr_device_class = SensorDeviceClass.WATER
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif type_number == 3:
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
            self._attr_device_class = SensorDeviceClass.GAS
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif type_number == 5:
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif type_number == 8:
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
            # Combined multi-tariff strings are not valid numeric ENERGY values
            if values_count <= 1:
                self._attr_device_class = SensorDeviceClass.ENERGY
                self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def current_meter(self):
        """Return current meter object from API cache."""
        return self.api.get_sensor(self.flat_id, self.meter_id)

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.current_meter.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        meter = self.current_meter
        attrs: dict[str, Any] = {
            "condition": meter.state,
            "sn": meter.sn,
            "type": meter.type,
            "meter_id": meter.meter_id,
            "input": meter.input,
            "approve_dt": meter.approve_dt,
            "controller_sn": self.controller_sn,
        }
        if meter.type_number == 8:
            attrs.update(
                {
                    "t1": meter.t1,
                    "t2": meter.t2,
                    "t3": meter.t3,
                    "t4": meter.t4,
                }
            )
        return attrs


class SauresBinarySensor(SauresEntity, BinarySensorEntity):
    """Representation of a Saures binary sensor."""

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
        """Initialize the binary sensor."""
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

    @property
    def current_sensor(self):
        """Return current binary sensor object from API cache."""
        return self.api.get_binarysensor(self.flat_id, self.meter_id)

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        meter = self.current_sensor
        value = meter.value
        if meter.state is not None and str(meter.state).upper() == "ОБРЫВ":
            value = True
        return _parse_bool_state(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        meter = self.current_sensor
        return {
            "condition": meter.state,
            "sn": meter.sn,
            "type": meter.type,
            "meter_id": meter.meter_id,
            "input": meter.input,
            "controller_sn": self.controller_sn,
        }


class SauresControllerSensor(SauresEntity, SensorEntity):
    """Representation of a Saures controller sensor."""

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
        """Initialize the controller sensor."""
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

    @property
    def current_controller_info(self):
        """Return current controller object from API cache."""
        return self.api.get_controller(self.flat_id, self.serial_number)

    @property
    def native_value(self) -> Any:
        """Return the state of the controller."""
        return self.current_controller_info.state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        my_controller = self.current_controller_info
        return {
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
        }


class SauresSwitch(SauresEntity, SwitchEntity):
    """Representation of a Saures switch."""

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
        """Initialize the switch."""
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

    @property
    def current_meter(self):
        """Return current switch object from API cache."""
        return self.api.get_switch(self.flat_id, self.meter_id)

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return _parse_bool_state(self.current_meter.value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        meter = self.current_meter
        return {
            "condition": meter.state,
            "sn": meter.sn,
            "type": meter.type,
            "meter_id": meter.meter_id,
            "input": meter.input,
            "approve_dt": meter.approve_dt,
            "controller_sn": self.controller_sn,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        result = await self.api.set_command(self.meter_id, CONF_COMMAND_ACTIVATE)
        if result:
            await self.api.async_get_switches(self.flat_id, True)
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        result = await self.api.set_command(self.meter_id, CONF_COMMAND_DEACTIVATE)
        if result:
            await self.api.async_get_switches(self.flat_id, True)
            await self.coordinator.async_request_refresh()
