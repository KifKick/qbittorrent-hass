"""Binary sensor platform for the qBittorrent integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import QBittorrentConfigEntry, QBittorrentCoordinator
from .entity import QBittorrentEntity


class QBittorrentConnectivitySensor(QBittorrentEntity, BinarySensorEntity):
    """Whether the integration currently has a working connection to qBittorrent."""

    _attr_translation_key = "connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = None

    def __init__(self, coordinator: QBittorrentCoordinator) -> None:
        super().__init__(coordinator, "connectivity")

    @property
    def available(self) -> bool:
        # This entity reports connectivity itself, so it must stay available
        # even when the coordinator's last update failed.
        return True

    @property
    def is_on(self) -> bool:
        if not self.coordinator.last_update_success:
            return False
        status = self.coordinator.data.server_state.get("connection_status")
        return status is not None and status != "disconnected"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: QBittorrentConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up qBittorrent binary sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([QBittorrentConnectivitySensor(coordinator)])
