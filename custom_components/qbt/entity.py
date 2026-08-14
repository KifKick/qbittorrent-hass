"""Base entity for the qBittorrent integration."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from qbittorrentapi.exceptions import (
    APIConnectionError,
    Conflict409Error,
    Forbidden403Error,
    LoginFailed,
    NotFound404Error,
)

from .const import CONF_USE_HTTPS, DOMAIN
from .coordinator import QBittorrentCoordinator


class QBittorrentEntity(CoordinatorEntity[QBittorrentCoordinator]):
    """Base entity tying every qBittorrent entity to a single device per entry."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: QBittorrentCoordinator, unique_id_suffix: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        """Build device info from the entry and the latest coordinator data.

        Computed on access (instead of cached in __init__) so the device
        registry picks up app_version/web_api_version once they're fetched,
        rather than staying frozen at whatever was known when the entity was
        created (often before the first refresh completed).
        """
        entry = self.coordinator.config_entry
        host = entry.data["host"]
        port = entry.data["port"]
        scheme = "https" if entry.data.get(CONF_USE_HTTPS) else "http"
        data = self.coordinator.data

        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="qBittorrent",
            model=f"Web API {data.web_api_version}" if data else None,
            sw_version=data.app_version if data else None,
            configuration_url=f"{scheme}://{host}:{port}",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def _async_write(self, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        """Run a synchronous client write call in the executor, mapping API errors.

        Mirrors the error handling in services._async_call so switch/number/button
        writes behave the same as service calls: connection issues and rejected
        requests surface as a readable HomeAssistantError, and truly invalid
        credentials trigger the reauth flow, instead of an unhandled traceback.
        """
        try:
            return await self.hass.async_add_executor_job(partial(func, *args, **kwargs))
        except LoginFailed as err:
            self.coordinator.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                "qBittorrent authentication failed; re-authentication has been requested"
            ) from err
        except Forbidden403Error as err:
            raise HomeAssistantError(f"qBittorrent rejected the request: {err}") from err
        except NotFound404Error as err:
            raise HomeAssistantError(f"Torrent(s) or item not found: {err}") from err
        except Conflict409Error as err:
            raise HomeAssistantError(
                f"qBittorrent rejected the request due to a conflicting state: {err}"
            ) from err
        except APIConnectionError as err:
            raise HomeAssistantError(f"Cannot reach qBittorrent: {err}") from err
        except (NotImplementedError, AttributeError) as err:
            raise HomeAssistantError(
                f"This action is not supported by the connected qBittorrent/library version: {err}"
            ) from err
