"""Клиент облачного API Saures."""

from __future__ import annotations

import asyncio
import datetime
import logging
import socket
from typing import Any

import aiohttp
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .classes import SauresController, SauresSensor
from .const import CONF_BINARY_SENSORS_DEF, CONF_OVERCONSUMPTION_METER_TYPES, CONF_SWITCH_DEF, STATE_OVERCONSUMPTION

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://api.saures.ru/1.0"
# Official docs / working community configs use HTTPie UA.
# Minimal "chrome" is often rejected by Saures edge/WAF (connection reset).
API_HEADERS = {
    "User-Agent": "HTTPie/3.2.2",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}
REQUEST_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3

CONTROLLER_NAMES = {
    "1.3": "счетчик C1",
    "1.4": "счетчик C1",
    "1.5": "счетчик C1",
    "3.1": "контроллер R1(до 2017)",
    "3.2": "контроллер R1(до 2017)",
    "3.4": "контроллер R1 8 (2017-2018)",
    "3.5": "контроллер R1 4 (после 2018)",
    "4.0": "контроллер R2",
    "4.1": "контроллер R4",
    "6.3": "контроллер R5",
    "7.2": "контроллер R6",
    "8.2": "контроллер R7(до 2020)",
    "8.3": "контроллер R7(после 2020)",
    "9.1": "контроллер R8(после 2022)",
}


class SauresHA:
    """Обёртка над API Saures: авторизация, объекты, показания и команды."""

    def __init__(
        self,
        hass: Any,
        email: str,
        password: str,
        is_debug: bool,
        userflats: list | dict | str,
    ) -> None:
        """Инициализировать клиент API."""
        self._email = email
        self._password = password
        self._debug = bool(is_debug)
        self._last_login_time = datetime.datetime(2000, 1, 1, 1, 1, 1)
        self._last_update_time_dict: dict[Any, datetime.datetime] = {}
        self._data: dict[Any, Any] = {}
        self._sensors: dict[Any, list] = {}
        self._controllers: dict[Any, list] = {}
        self._binarysensors: dict[Any, list] = {}
        self._switches: dict[Any, list] = {}
        self._flats: dict[Any, str] | list = {}
        self.userflats = userflats or []
        self._hass = hass
        self._sid = ""
        self._sid_renewal = False
        self._auth_lock = asyncio.Lock()
        self._session: aiohttp.ClientSession | None = None

    @property
    def flats(self):
        """Вернуть список/словарь настроенных объектов (квартир)."""
        return self._flats

    def _get_session(self) -> aiohttp.ClientSession:
        """Получить отдельную HTTP-сессию (IPv4) с заголовками для Saures."""
        if self._session is None or self._session.closed:
            # Prefer IPv4: IPv6 routes often cause Connection reset by peer.
            self._session = async_create_clientsession(
                self._hass,
                family=socket.AF_INET,
                headers=API_HEADERS,
                timeout=aiohttp.ClientTimeout(total=60),
            )
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Выполнить HTTP-запрос к API с повторами при обрыве соединения."""
        url = f"{API_BASE}{path}"
        last_error: Exception | None = None

        for attempt in range(1, REQUEST_ATTEMPTS + 1):
            try:
                session = self._get_session()
                async with session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    headers=API_HEADERS,
                ) as response:
                    payload = await response.json(content_type=None)
                    if response.status >= 400:
                        raise RuntimeError(
                            f"HTTP {response.status} for {path}: {payload}"
                        )
                    return payload
            except (
                aiohttp.ClientOSError,
                aiohttp.ServerDisconnectedError,
                aiohttp.ClientConnectorError,
                asyncio.TimeoutError,
            ) as err:
                last_error = err
                _LOGGER.warning(
                    "Saures request %s %s failed (attempt %s/%s): %s",
                    method,
                    path,
                    attempt,
                    REQUEST_ATTEMPTS,
                    err,
                )
                # Recreate session after transport errors
                if self._session is not None and not self._session.closed:
                    await self._session.close()
                self._session = None
                if attempt < REQUEST_ATTEMPTS:
                    await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

        raise RuntimeError(
            f"Saures request failed after {REQUEST_ATTEMPTS} attempts: {last_error}"
        ) from last_error

    async def auth(self) -> bool:
        """Авторизоваться в API Saures и сохранить идентификатор сессии (sid)."""
        try:
            now = datetime.datetime.now()
            period = now - self._last_login_time
            if (period.total_seconds() / 60) < 5 and self._sid:
                return True

            async with self._auth_lock:
                now = datetime.datetime.now()
                period = now - self._last_login_time
                if (period.total_seconds() / 60) < 5 and self._sid:
                    return True

                result = await self._request(
                    "POST",
                    "/login",
                    data={"email": self._email, "password": self._password},
                )
                if not result:
                    raise RuntimeError("Invalid credentials")
                if result.get("errors"):
                    raise RuntimeError(result["errors"][0]["msg"])

                self._sid = result["data"]["sid"]
                self._last_login_time = datetime.datetime.now()
                return result.get("status") != "bad"
        except Exception as err:  # noqa: BLE001
            self._sid = ""
            _LOGGER.error("Saures auth failed: %s", err)
            return False

    async def async_get_flats(self, hass) -> dict[Any, str]:
        """Получить словарь объектов пользователя: id -> описание."""
        if self.userflats:
            if isinstance(self.userflats, dict):
                self._flats = self.userflats
            else:
                self._flats = {str(flat_id): str(flat_id) for flat_id in self.userflats}
            return self._flats

        flats: dict[Any, str] = {}
        try:
            if not await self.auth():
                self._flats = flats
                return flats

            result = await self._request(
                "GET",
                "/user/objects",
                params={"sid": self._sid},
            )
            for val in result.get("data", {}).get("objects", []):
                flats[val.get("id")] = (
                    f"{val.get('label')}:{val.get('house')}:{val.get('number')}"
                )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Failed to load flats: %s", err)

        self._flats = flats
        return flats

    @staticmethod
    def get_controller_name(version_id: str | None) -> str:
        """Вернуть читаемое название модели контроллера по версии hardware."""
        if not version_id:
            return "контроллер Saures"
        return CONTROLLER_NAMES.get(str(version_id), f"контроллер ({version_id})")

    async def set_command(self, meter_id: Any, command_text: str) -> bool:
        """Отправить команду управления устройству (например, крану)."""
        try:
            if not await self.auth():
                return False

            result = await self._request(
                "POST",
                "/meter/control",
                data={"sid": self._sid, "id": meter_id, "command": command_text},
            )
            if not result:
                raise RuntimeError("Command failed")

            ok = result.get("status") != "bad"
            if not ok:
                msg = result.get("errors", [{}])[0].get("msg", "unknown")
                _LOGGER.warning(
                    "Command failed (command=%s, meter_id=%s): %s",
                    command_text,
                    meter_id,
                    msg,
                )
            return ok
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("set_command error: %s", err)
            return False

    async def async_get_data(self, flat_id: Any, reload: bool = False) -> list:
        """Загрузить и закэшировать контроллеры/метры для объекта."""
        now = datetime.datetime.now()
        last_update = self._last_update_time_dict.get(
            flat_id, datetime.datetime(2000, 1, 1, 1, 1, 1)
        )
        period = now - last_update
        if (period.total_seconds() / 60) >= 5 or reload:
            self._last_update_time_dict[flat_id] = datetime.datetime.now()
            if await self.auth():
                try:
                    data = await self._request(
                        "GET",
                        "/object/meters",
                        params={"id": str(flat_id), "sid": self._sid},
                    )
                    self._data[flat_id] = data.get("data", {}).get("sensors", [])
                except Exception as err:  # noqa: BLE001
                    _LOGGER.error("Failed to load meters for flat %s: %s", flat_id, err)

        return self._data.get(flat_id, [])

    async def async_get_controllers(self, flat_id: Any) -> list:
        """Вернуть список контроллеров объекта."""
        controllers = await self.async_get_data(flat_id)
        self._controllers[flat_id] = controllers
        return controllers

    def get_controller(self, flat_id: Any, sn: str) -> SauresController:
        """Найти контроллер объекта по серийному номеру."""
        controllers = self._controllers.get(flat_id, [])
        return next(
            (
                SauresController(controller)
                for controller in controllers
                if controller.get("sn") == sn
            ),
            SauresController({}),
        )

    @staticmethod
    def _meters_with_controller(controllers: list) -> list[dict[str, Any]]:
        """Развернуть метры и сохранить данные родительского контроллера."""
        results: list[dict[str, Any]] = []
        for controller in controllers or []:
            controller_sn = controller.get("sn")
            if not controller_sn:
                continue
            for meter in controller.get("meters", []) or []:
                item = dict(meter)
                item["controller_sn"] = controller_sn
                item["controller_name"] = controller.get("name")
                item["controller_hardware"] = controller.get("hardware")
                item["controller_firmware"] = controller.get("firmware")
                results.append(item)
        return results

    async def async_get_binary_sensors(self, flat_id: Any) -> list:
        """Вернуть бинарные датчики объекта (протечка, состояние крана и т.п.)."""
        controllers = await self.async_get_data(flat_id)
        results = []
        for obj in self._meters_with_controller(controllers):
            objtype = obj.get("type", {}).get("number")
            if objtype in CONF_BINARY_SENSORS_DEF:
                results.append(obj)
        self._binarysensors[flat_id] = results
        return results

    async def async_get_sensors(self, flat_id: Any) -> list:
        """Вернуть обычные счётчики объекта (не binary и не switch)."""
        controllers = await self.async_get_data(flat_id)
        results = []
        for obj in self._meters_with_controller(controllers):
            objtype = obj.get("type", {}).get("number")
            if (
                objtype not in CONF_BINARY_SENSORS_DEF
                and objtype not in CONF_SWITCH_DEF
            ):
                results.append(obj)
        self._sensors[flat_id] = results
        return results

    def get_sensor(self, flat_id: Any, sensor_id: Any) -> SauresSensor:
        """Получить счётчик из кэша по meter_id."""
        for obj in self._sensors.get(flat_id, []):
            if obj.get("meter_id") == sensor_id:
                return SauresSensor(obj)
        return SauresSensor({})

    def get_suspicious_consumption_meters(
        self, flat_id: Any, controller_sn: str
    ) -> list[dict[str, Any]]:
        """Список счётчиков контроллера с активным подозрительным расходом."""
        result: list[dict[str, Any]] = []
        for obj in self._sensors.get(flat_id, []):
            if obj.get("controller_sn") != controller_sn:
                continue
            type_number = obj.get("type", {}).get("number")
            if type_number not in CONF_OVERCONSUMPTION_METER_TYPES:
                continue
            state = obj.get("state") or {}
            if state.get("number") != STATE_OVERCONSUMPTION:
                continue
            result.append(
                {
                    "meter_id": obj.get("meter_id"),
                    "meter_name": obj.get("meter_name"),
                    "condition": state.get("name"),
                    "condition_number": state.get("number"),
                    "type": obj.get("type", {}).get("name"),
                    "input": obj.get("input"),
                }
            )
        return result

    def get_binarysensor(self, flat_id: Any, sensor_id: Any) -> SauresSensor:
        """Получить бинарный датчик из кэша по meter_id."""
        for obj in self._binarysensors.get(flat_id, []):
            if obj.get("meter_id") == sensor_id:
                return SauresSensor(obj)
        return SauresSensor({})

    async def async_get_switches(self, flat_id: Any, reload: bool) -> list:
        """Вернуть управляемые устройства (краны) объекта."""
        controllers = await self.async_get_data(flat_id, reload=reload)
        results = []
        for obj in self._meters_with_controller(controllers):
            if obj.get("type", {}).get("number") in CONF_SWITCH_DEF:
                results.append(obj)
        self._switches[flat_id] = results
        return results

    def get_switch(self, flat_id: Any, switch_id: Any) -> SauresSensor:
        """Получить кран/switch из кэша по meter_id."""
        for obj in self._switches.get(flat_id, []):
            if obj.get("meter_id") == switch_id:
                return SauresSensor(obj)
        return SauresSensor({})

    async def async_fetch_data(self, *, delay_between_flats: float = 0) -> None:
        """Обновить объекты и все связанные кэши показаний.

        Args:
            delay_between_flats: пауза между объектами (сек). На первом старте
                должна быть 0 — иначе Home Assistant отменяет setup по таймауту.
        """
        try:
            if not await self.auth():
                raise RuntimeError("Authentication failed")

            flats = await self.async_get_flats(self._hass)
            self._flats = flats
            flat_ids = list(flats)
            for index, curflat in enumerate(flat_ids):
                try:
                    # Один запрос /object/meters наполняет все кэши объекта
                    await self.async_get_controllers(curflat)
                    await self.async_get_sensors(curflat)
                    await self.async_get_binary_sensors(curflat)
                    await self.async_get_switches(curflat, False)
                    if delay_between_flats > 0 and index < len(flat_ids) - 1:
                        await asyncio.sleep(delay_between_flats)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _LOGGER.exception("Error load data for flat %s", curflat)
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Error load data")
            raise
