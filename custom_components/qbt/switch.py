"""Switch platform for the qBittorrent integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import QBittorrentConfigEntry, QBittorrentCoordinator, QBittorrentData
from .entity import QBittorrentEntity


@dataclass(frozen=True, kw_only=True)
class QBittorrentSwitchEntityDescription(SwitchEntityDescription):
    """Describes a qBittorrent switch entity."""

    is_on_fn: Callable[[QBittorrentData], bool]
    turn_on_fn: Callable[[Any], None]
    turn_off_fn: Callable[[Any], None]


SWITCH_DESCRIPTIONS: tuple[QBittorrentSwitchEntityDescription, ...] = (
    QBittorrentSwitchEntityDescription(
        key="alt_speed_limits",
        translation_key="alt_speed_limits",
        icon="mdi:speedometer-slow",
        is_on_fn=lambda data: bool(data.server_state.get("use_alt_speed_limits")),
        turn_on_fn=lambda client: client.transfer_set_speed_limits_mode(intended_state=True),
        turn_off_fn=lambda client: client.transfer_set_speed_limits_mode(intended_state=False),
    ),
    QBittorrentSwitchEntityDescription(
        key="dht",
        translation_key="dht",
        icon="mdi:lan",
        entity_category=None,
        is_on_fn=lambda data: bool(data.preferences.get("dht")),
        turn_on_fn=lambda client: client.app_set_preferences({"dht": True}),
        turn_off_fn=lambda client: client.app_set_preferences({"dht": False}),
    ),
    QBittorrentSwitchEntityDescription(
        key="queueing_enabled",
        translation_key="queueing_enabled",
        icon="mdi:sort-numeric-ascending",
        entity_category=None,
        is_on_fn=lambda data: bool(data.preferences.get("queueing_enabled")),
        turn_on_fn=lambda client: client.app_set_preferences({"queueing_enabled": True}),
        turn_off_fn=lambda client: client.app_set_preferences({"queueing_enabled": False}),
    ),
)


class QBittorrentSwitch(QBittorrentEntity, SwitchEntity):
    """Representation of a global qBittorrent toggle."""

    entity_description: QBittorrentSwitchEntityDescription

    def __init__(
        self,
        coordinator: QBittorrentCoordinator,
        description: QBittorrentSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.is_on_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(
            self.entity_description.turn_on_fn, self.coordinator.client
        )
        await self.coordinator.async_request_refresh_after_write()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.async_add_executor_job(
            self.entity_description.turn_off_fn, self.coordinator.client
        )
        await self.coordinator.async_request_refresh_after_write()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: QBittorrentConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up qBittorrent switches from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        QBittorrentSwitch(coordinator, description) for description in SWITCH_DESCRIPTIONS
    )
