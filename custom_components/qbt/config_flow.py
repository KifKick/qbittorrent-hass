"""Config flow for the qBittorrent integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from qbittorrentapi.exceptions import (
    APIConnectionError,
    Forbidden403Error,
    LoginFailed,
    UnsupportedQbittorrentVersion,
)

from .const import (
    AUTH_METHOD_API_KEY,
    AUTH_METHOD_PASSWORD,
    CONF_API_KEY,
    CONF_AUTH_METHOD,
    CONF_ENABLE_TORRENT_LIST_SENSOR,
    CONF_MAX_TORRENTS_IN_ATTRIBUTES,
    CONF_PATH,
    CONF_SCAN_INTERVAL,
    CONF_USE_HTTPS,
    CONF_VERIFY_SSL,
    DEFAULT_ENABLE_TORRENT_LIST_SENSOR,
    DEFAULT_MAX_TORRENTS_IN_ATTRIBUTES,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USE_HTTPS,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MAX_MAX_TORRENTS_IN_ATTRIBUTES,
    MAX_SCAN_INTERVAL,
    MIN_MAX_TORRENTS_IN_ATTRIBUTES,
    MIN_SCAN_INTERVAL,
)
from .coordinator import build_client

_LOGGER = logging.getLogger(__name__)


def _connection_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("host", default=defaults.get("host", "")): TextSelector(),
            vol.Required("port", default=defaults.get("port", DEFAULT_PORT)): NumberSelector(
                NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_USE_HTTPS, default=defaults.get(CONF_USE_HTTPS, DEFAULT_USE_HTTPS)
            ): BooleanSelector(),
            vol.Required(
                CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            ): BooleanSelector(),
            vol.Optional(CONF_PATH, default=defaults.get(CONF_PATH, "")): TextSelector(),
            vol.Required(
                CONF_AUTH_METHOD, default=defaults.get(CONF_AUTH_METHOD, AUTH_METHOD_PASSWORD)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[AUTH_METHOD_PASSWORD, AUTH_METHOD_API_KEY],
                    translation_key=CONF_AUTH_METHOD,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _auth_schema(auth_method: str, defaults: dict[str, Any]) -> vol.Schema:
    if auth_method == AUTH_METHOD_API_KEY:
        return vol.Schema(
            {
                vol.Required(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
    return vol.Schema(
        {
            vol.Required("username", default=defaults.get("username", "")): TextSelector(),
            vol.Required("password"): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
    )


async def _async_validate(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the connection info by logging in and fetching version info.

    Returns extra info to store (title). Raises on failure so the caller
    can map the exception to a form error.
    """

    def _connect() -> dict[str, Any]:
        # Unlike the coordinator's long-lived client, it's safe (and useful) for
        # this short-lived validation client to fail loudly on an unsupported
        # version: it's used once and discarded, so it can't get stuck retrying.
        client = build_client(data, raise_for_unsupported_version=True)
        client.auth_log_in()
        return {
            "app_version": client.app_version(),
            "web_api_version": client.app_web_api_version(),
        }

    return await hass.async_add_executor_job(_connect)


class QBittorrentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for qBittorrent."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect connection details (host, port, scheme, auth method)."""
        if user_input is not None:
            # NumberSelector always yields a float; qBittorrent's port is an int
            # and the unique_id (host:port) must format consistently.
            user_input["port"] = int(user_input["port"])
            self._data.update(user_input)
            return await self.async_step_auth()

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(self._data),
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect credentials matching the chosen auth method and validate."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)

            await self.async_set_unique_id(f"{self._data['host']}:{self._data['port']}")
            self._abort_if_unique_id_configured()

            try:
                await _async_validate(self.hass, self._data)
            except LoginFailed:
                errors["base"] = "invalid_auth"
            except Forbidden403Error:
                # qBittorrent's brute-force protection bans the client IP after
                # too many failed attempts; every subsequent login (even with
                # correct credentials) gets 403 until the ban clears. This is
                # a distinct error from wrong credentials (LoginFailed above).
                errors["base"] = "banned"
            except UnsupportedQbittorrentVersion:
                _LOGGER.warning(
                    "Connected to an unsupported qBittorrent version; continuing anyway"
                )
            except APIConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating qBittorrent connection")
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(
                    title=f"qBittorrent ({self._data['host']})",
                    data=self._data,
                )

        return self.async_show_form(
            step_id="auth",
            data_schema=_auth_schema(self._data[CONF_AUTH_METHOD], self._data),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when credentials stop working."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        self._data = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-collect credentials only, keeping the existing connection settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)

            try:
                await _async_validate(self.hass, self._data)
            except LoginFailed:
                errors["base"] = "invalid_auth"
            except Forbidden403Error:
                errors["base"] = "banned"
            except APIConnectionError:
                errors["base"] = "cannot_connect"
            except UnsupportedQbittorrentVersion:
                pass
            except Exception:
                _LOGGER.exception("Unexpected error validating qBittorrent connection")
                errors["base"] = "unknown"

            if not errors:
                assert self._reauth_entry is not None
                return self.async_update_reload_and_abort(
                    self._reauth_entry, data=self._data
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_auth_schema(self._data[CONF_AUTH_METHOD], self._data),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return QBittorrentOptionsFlow()


class QBittorrentOptionsFlow(OptionsFlow):
    """Handle options for a qBittorrent config entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage runtime-adjustable options."""
        if user_input is not None:
            # NumberSelector always yields a float; both options are used as
            # ints (timedelta seconds, list slice index) further down the line.
            user_input[CONF_SCAN_INTERVAL] = int(user_input[CONF_SCAN_INTERVAL])
            user_input[CONF_MAX_TORRENTS_IN_ATTRIBUTES] = int(
                user_input[CONF_MAX_TORRENTS_IN_ATTRIBUTES]
            )
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_ENABLE_TORRENT_LIST_SENSOR,
                    default=options.get(
                        CONF_ENABLE_TORRENT_LIST_SENSOR, DEFAULT_ENABLE_TORRENT_LIST_SENSOR
                    ),
                ): BooleanSelector(),
                vol.Required(
                    CONF_MAX_TORRENTS_IN_ATTRIBUTES,
                    default=options.get(
                        CONF_MAX_TORRENTS_IN_ATTRIBUTES, DEFAULT_MAX_TORRENTS_IN_ATTRIBUTES
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_MAX_TORRENTS_IN_ATTRIBUTES,
                        max=MAX_MAX_TORRENTS_IN_ATTRIBUTES,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
