"""Number platform for the qBittorrent integration.

These entities read/write raw qBittorrent preference keys (the same
mechanism backing the generic `set_preferences` service), so their value
only refreshes on the coordinator's slow cycle (every Nth poll) — writes
force an immediate refresh via `async_request_refresh_after_write`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import QBittorrentConfigEntry, QBittorrentCoordinator
from .entity import QBittorrentEntity


@dataclass(frozen=True, kw_only=True)
class QBittorrentNumberEntityDescription(NumberEntityDescription):
    """Describes a qBittorrent number entity backed by a preference key."""

    preference_key: str
    to_preference_value: Callable[[float], Any] = int


NUMBER_DESCRIPTIONS: tuple[QBittorrentNumberEntityDescription, ...] = (
    QBittorrentNumberEntityDescription(
        key="listen_port",
        translation_key="listen_port",
        preference_key="listen_port",
        icon="mdi:ethernet",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="max_connec",
        translation_key="max_connec",
        preference_key="max_connec",
        icon="mdi:lan-connect",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-1,
        native_max_value=100000,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="max_connec_per_torrent",
        translation_key="max_connec_per_torrent",
        preference_key="max_connec_per_torrent",
        icon="mdi:lan-connect",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-1,
        native_max_value=100000,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="max_uploads",
        translation_key="max_uploads",
        preference_key="max_uploads",
        icon="mdi:upload-network",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-1,
        native_max_value=10000,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="max_uploads_per_torrent",
        translation_key="max_uploads_per_torrent",
        preference_key="max_uploads_per_torrent",
        icon="mdi:upload-network",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-1,
        native_max_value=10000,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="dl_limit",
        translation_key="dl_limit",
        preference_key="dl_limit",
        icon="mdi:download",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.KIBIBYTES_PER_SECOND,
        native_min_value=0,
        native_max_value=1048576,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="up_limit",
        translation_key="up_limit",
        preference_key="up_limit",
        icon="mdi:upload",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.KIBIBYTES_PER_SECOND,
        native_min_value=0,
        native_max_value=1048576,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="alt_dl_limit",
        translation_key="alt_dl_limit",
        preference_key="alt_dl_limit",
        icon="mdi:download",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.KIBIBYTES_PER_SECOND,
        native_min_value=0,
        native_max_value=1048576,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="alt_up_limit",
        translation_key="alt_up_limit",
        preference_key="alt_up_limit",
        icon="mdi:upload",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.KIBIBYTES_PER_SECOND,
        native_min_value=0,
        native_max_value=1048576,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="max_active_downloads",
        translation_key="max_active_downloads",
        preference_key="max_active_downloads",
        icon="mdi:download-multiple",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-1,
        native_max_value=1000,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="max_active_uploads",
        translation_key="max_active_uploads",
        preference_key="max_active_uploads",
        icon="mdi:upload-multiple",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-1,
        native_max_value=1000,
        native_step=1,
        mode=NumberMode.BOX,
    ),
    QBittorrentNumberEntityDescription(
        key="max_active_torrents",
        translation_key="max_active_torrents",
        preference_key="max_active_torrents",
        icon="mdi:format-list-numbered",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-1,
        native_max_value=1000,
        native_step=1,
        mode=NumberMode.BOX,
    ),
)


class QBittorrentNumber(QBittorrentEntity, NumberEntity):
    """A qBittorrent setting exposed as an editable number."""

    entity_description: QBittorrentNumberEntityDescription

    def __init__(
        self,
        coordinator: QBittorrentCoordinator,
        description: QBittorrentNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        return self.coordinator.data.preferences.get(self.entity_description.preference_key)

    async def async_set_native_value(self, value: float) -> None:
        preference_key = self.entity_description.preference_key
        new_value = self.entity_description.to_preference_value(value)
        await self._async_write(
            self.coordinator.client.app_set_preferences, {preference_key: new_value}
        )
        await self.coordinator.async_request_refresh_after_write()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: QBittorrentConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up qBittorrent number entities from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        QBittorrentNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS
    )
