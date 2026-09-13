"""Модели данных ответа API Saures."""

from __future__ import annotations

from typing import Any


class SauresController:
    """Снимок состояния контроллера Saures."""

    def __init__(self, data: dict[str, Any] | None) -> None:
        """Создать объект контроллера из JSON-ответа API."""
        data = data or {}
        self.data = data
        self.name = data.get("name") or data.get("sn")
        self.sn = data.get("sn")
        self.battery = data.get("bat")
        self.ssid = data.get("ssid")
        self.local_ip = data.get("local_ip")
        self.firmware = data.get("firmware")
        self.readout_dt = data.get("readout_dt")
        self.request_dt = data.get("request_dt")
        self.state = "OK"
        self.rssi = data.get("rssi")
        self.hardware = data.get("hardware")
        self.new_firmware = data.get("new_firmware")
        self.last_connection = data.get("last_connection")
        self.last_connection_warning = data.get("last_connection_warning")
        self.check_hours = data.get("check_hours")
        self.check_period_display = data.get("check_period_display")
        self.requests = data.get("requests")
        self.log = data.get("log")
        self.cap_state = bool(data.get("cap_state"))
        self.power_supply = bool(data.get("power_supply"))


class SauresSensor:
    """Снимок показаний счётчика или датчика Saures."""

    def __init__(self, data: dict[str, Any] | None) -> None:
        """Создать объект счётчика/датчика из JSON-ответа API."""
        data = data or {}
        self.data = data
        self.name = data.get("meter_name")
        raw_type = data.get("type", {}).get("number")
        try:
            self.type_number = int(raw_type) if raw_type is not None else None
        except (TypeError, ValueError):
            self.type_number = None
        self.type = data.get("type", {}).get("name")
        state = data.get("state") or {}
        self.state = state.get("name")
        self.state_number = state.get("number")
        self.sn = data.get("sn")
        self.value = data.get("value")
        self.meter_id = data.get("meter_id")
        self.input = data.get("input")
        self.approve_dt = data.get("approve_dt")
        self.t1 = "-"
        self.t2 = "-"
        self.t3 = "-"
        self.t4 = "-"

        self.values = data.get("vals") or []

        # Многотарифная склейка "t1/t2/..." — только для электроэнергии (тип 8).
        # У других типов (давление и т.п.) при нескольких vals берём первое значение.
        if self.type_number == 8 and len(self.values) > 1:
            self.value = "/".join(str(v) for v in self.values)
            if len(self.values) >= 1:
                self.t1 = self.values[0]
            if len(self.values) >= 2:
                self.t2 = self.values[1]
            if len(self.values) >= 3:
                self.t3 = self.values[2]
            if len(self.values) >= 4:
                self.t4 = self.values[3]
        elif len(self.values) >= 1:
            self.value = self.values[0]
            self.t1 = self.values[0]
            if len(self.values) >= 2:
                self.t2 = self.values[1]
            if len(self.values) >= 3:
                self.t3 = self.values[2]
            if len(self.values) >= 4:
                self.t4 = self.values[3]
