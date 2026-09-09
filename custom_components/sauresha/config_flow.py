"""Поток настройки (config flow) интеграции SauresHA."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .api import SauresHA
from .const import (
    CONF_FLATS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class SaureshaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Обработчик первичной настройки интеграции через UI."""

    VERSION = 1

    def __init__(self) -> None:
        """Инициализировать поток настройки."""
        self._errors: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Обработать первый шаг: ввод email, пароля и интервала опроса."""
        self._errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
            self._abort_if_unique_id_configured()

            api = SauresHA(
                self.hass,
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                True,
                [],
            )
            if not await api.auth():
                self._errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )

            return self._show_config_form(user_input)

        return self._show_config_form(
            {
                CONF_EMAIL: "",
                CONF_PASSWORD: "",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            }
        )

    def _show_config_form(
        self, user_input: dict[str, Any]
    ) -> ConfigFlowResult:
        """Показать форму первичной настройки."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                    vol.Required(
                        CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, "")
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                }
            ),
            errors=self._errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Вернуть обработчик дополнительных параметров интеграции."""
        return SaureshaOptionsFlowHandler()


class SaureshaOptionsFlowHandler(OptionsFlow):
    """Обработчик параметров: выбор объектов (квартир) Saures."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Показать и сохранить список объектов для опроса."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        flats: dict[str, str] = {}
        try:
            api = SauresHA(
                self.hass,
                self.config_entry.data[CONF_EMAIL],
                self.config_entry.data[CONF_PASSWORD],
                True,
                [],
            )
            flats = await api.async_get_flats(self.hass)
            if not flats:
                errors["base"] = "cannot_connect"
        except Exception:
            _LOGGER.exception("Failed to load flats for options")
            errors["base"] = "cannot_connect"
            flats = {}

        selected = self.config_entry.options.get(CONF_FLATS, [])
        flat_options = {
            str(flat_id): f"{label} ({flat_id})" for flat_id, label in flats.items()
        }

        # Keep previously selected flats even if API temporarily fails
        for flat_id in selected:
            flat_options.setdefault(str(flat_id), str(flat_id))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_FLATS,
                        default=[str(item) for item in selected],
                    ): cv.multi_select(flat_options)
                }
            ),
            errors=errors,
        )
