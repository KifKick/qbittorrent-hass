"""Sensor platform for the qBittorrent integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    CONF_ENABLE_TORRENT_LIST_SENSOR,
    CONF_MAX_TORRENTS_IN_ATTRIBUTES,
    DEFAULT_ENABLE_TORRENT_LIST_SENSOR,
    DEFAULT_MAX_TORRENTS_IN_ATTRIBUTES,
)
from .coordinator import QBittorrentConfigEntry, QBittorrentCoordinator, QBittorrentData
from .entity import QBittorrentEntity

CONNECTION_STATUS_OPTIONS = ["connected", "firewalled", "disconnected"]


def _connection_status(data: QBittorrentData) -> str | None:
    status = _server_state(data).get("connection_status")
    # Guard against qBittorrent adding a new status value in the future: an
    # unrecognized string would otherwise fail HA's ENUM state validation and
    # make the sensor log errors instead of just going momentarily unknown.
    return status if status in CONNECTION_STATUS_OPTIONS else None


@dataclass(frozen=True, kw_only=True)
class QBittorrentSensorEntityDescription(SensorEntityDescription):
    """Describes a qBittorrent sensor entity."""

    value_fn: Callable[[QBittorrentData], StateType]
    attributes_fn: Callable[[QBittorrentData], dict[str, Any]] | None = None


def _server_state(data: QBittorrentData) -> dict[str, Any]:
    return data.server_state


SENSOR_DESCRIPTIONS: tuple[QBittorrentSensorEntityDescription, ...] = (
    QBittorrentSensorEntityDescription(
        key="dl_speed",
        translation_key="dl_speed",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABYTES_PER_SECOND,
        suggested_display_precision=2,
        value_fn=lambda data: _server_state(data).get("dl_info_speed"),
    ),
    QBittorrentSensorEntityDescription(
        key="up_speed",
        translation_key="up_speed",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABYTES_PER_SECOND,
        suggested_display_precision=2,
        value_fn=lambda data: _server_state(data).get("up_info_speed"),
    ),
    QBittorrentSensorEntityDescription(
        key="dl_data_session",
        translation_key="dl_data_session",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _server_state(data).get("dl_info_data"),
    ),
    QBittorrentSensorEntityDescription(
        key="up_data_session",
        translation_key="up_data_session",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _server_state(data).get("up_info_data"),
    ),
    QBittorrentSensorEntityDescription(
        key="dl_limit",
        translation_key="dl_limit",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABYTES_PER_SECOND,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _server_state(data).get("dl_rate_limit"),
    ),
    QBittorrentSensorEntityDescription(
        key="up_limit",
        translation_key="up_limit",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.MEGABYTES_PER_SECOND,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _server_state(data).get("up_rate_limit"),
    ),
    QBittorrentSensorEntityDescription(
        key="global_ratio",
        translation_key="global_ratio",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:scale-balance",
        value_fn=lambda data: _server_state(data).get("global_ratio"),
    ),
    QBittorrentSensorEntityDescription(
        key="free_space",
        translation_key="free_space",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=1,
        value_fn=lambda data: _server_state(data).get("free_space_on_disk"),
    ),
    QBittorrentSensorEntityDescription(
        key="dht_nodes",
        translation_key="dht_nodes",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:lan",
        value_fn=lambda data: _server_state(data).get("dht_nodes"),
    ),
    QBittorrentSensorEntityDescription(
        key="total_peer_connections",
        translation_key="total_peer_connections",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:account-multiple",
        value_fn=lambda data: _server_state(data).get("total_peer_connections"),
    ),
    QBittorrentSensorEntityDescription(
        key="connection_status",
        translation_key="connection_status",
        device_class=SensorDeviceClass.ENUM,
        options=CONNECTION_STATUS_OPTIONS,
        value_fn=_connection_status,
    ),
    QBittorrentSensorEntityDescription(
        key="torrents_total",
        translation_key="torrents_total",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:file-multiple",
        value_fn=lambda data: data.counts_by_state.get("total"),
    ),
    QBittorrentSensorEntityDescription(
        key="torrents_downloading",
        translation_key="torrents_downloading",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:download",
        value_fn=lambda data: data.counts_by_state.get("downloading"),
    ),
    QBittorrentSensorEntityDescription(
        key="torrents_seeding",
        translation_key="torrents_seeding",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:upload",
        value_fn=lambda data: data.counts_by_state.get("seeding"),
    ),
    QBittorrentSensorEntityDescription(
        key="torrents_paused",
        translation_key="torrents_paused",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pause",
        value_fn=lambda data: data.counts_by_state.get("paused"),
    ),
    QBittorrentSensorEntityDescription(
        key="torrents_checking",
        translation_key="torrents_checking",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:file-search-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.counts_by_state.get("checking"),
    ),
    QBittorrentSensorEntityDescription(
        key="torrents_error",
        translation_key="torrents_error",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.counts_by_state.get("error"),
    ),
    QBittorrentSensorEntityDescription(
        key="categories_count",
        translation_key="categories_count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:label-multiple",
        value_fn=lambda data: len(data.categories),
    ),
    QBittorrentSensorEntityDescription(
        key="tags_count",
        translation_key="tags_count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tag-multiple",
        value_fn=lambda data: len(data.tags),
    ),
    QBittorrentSensorEntityDescription(
        key="app_version",
        translation_key="app_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
        value_fn=lambda data: data.app_version,
    ),
    QBittorrentSensorEntityDescription(
        key="webapi_version",
        translation_key="webapi_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:api",
        value_fn=lambda data: data.web_api_version,
    ),
    QBittorrentSensorEntityDescription(
        key="default_save_path",
        translation_key="default_save_path",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:folder-outline",
        value_fn=lambda data: data.default_save_path,
    ),
)


def _torrent_attributes(data: QBittorrentData, max_torrents: int) -> dict[str, Any]:
    # Sort by name so which torrents get truncated is stable and predictable
    # instead of depending on qBittorrent's sync_maindata response order.
    torrents = sorted(
        data.torrents.items(), key=lambda item: (item[1].get("name") or "").lower()
    )[:max_torrents]
    return {
        torrent_hash: {
            "name": torrent.get("name"),
            "state": torrent.get("state"),
            "progress": torrent.get("progress"),
            "dlspeed": torrent.get("dlspeed"),
            "upspeed": torrent.get("upspeed"),
            "category": torrent.get("category"),
            "tags": torrent.get("tags"),
            "save_path": torrent.get("save_path"),
            "ratio": torrent.get("ratio"),
            "size": torrent.get("size"),
            "eta": torrent.get("eta"),
        }
        for torrent_hash, torrent in torrents
    }


class QBittorrentSensor(QBittorrentEntity, SensorEntity):
    """Representation of a global qBittorrent statistic."""

    entity_description: QBittorrentSensorEntityDescription

    def __init__(
        self,
        coordinator: QBittorrentCoordinator,
        description: QBittorrentSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributes_fn is None:
            return None
        return self.entity_description.attributes_fn(self.coordinator.data)


class QBittorrentTorrentListSensor(QBittorrentEntity, SensorEntity):
    """Diagnostic sensor exposing the torrent list as attributes for hash lookup."""

    _attr_translation_key = "torrent_list"
    _attr_icon = "mdi:format-list-bulleted"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: QBittorrentCoordinator, max_torrents: int) -> None:
        super().__init__(coordinator, "torrent_list")
        self._max_torrents = max_torrents

    @property
    def native_value(self) -> StateType:
        return len(self.coordinator.data.torrents)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return _torrent_attributes(self.coordinator.data, self._max_torrents)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: QBittorrentConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up qBittorrent sensors from a config entry."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        QBittorrentSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    ]

    if entry.options.get(CONF_ENABLE_TORRENT_LIST_SENSOR, DEFAULT_ENABLE_TORRENT_LIST_SENSOR):
        max_torrents = entry.options.get(
            CONF_MAX_TORRENTS_IN_ATTRIBUTES, DEFAULT_MAX_TORRENTS_IN_ATTRIBUTES
        )
        entities.append(QBittorrentTorrentListSensor(coordinator, max_torrents))

    async_add_entities(entities)
