"""Base entity for the qBittorrent integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_USE_HTTPS, DOMAIN
from .coordinator import QBittorrentCoordinator


class QBittorrentEntity(CoordinatorEntity[QBittorrentCoordinator]):
    """Base entity tying every qBittorrent entity to a single device per entry."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: QBittorrentCoordinator, unique_id_suffix: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"

        host = entry.data["host"]
        port = entry.data["port"]
        scheme = "https" if entry.data.get(CONF_USE_HTTPS) else "http"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="qBittorrent",
            model=f"Web API {coordinator.data.web_api_version}" if coordinator.data else None,
            sw_version=coordinator.data.app_version if coordinator.data else None,
            configuration_url=f"{scheme}://{host}:{port}",
            entry_type=DeviceEntryType.SERVICE,
        )
