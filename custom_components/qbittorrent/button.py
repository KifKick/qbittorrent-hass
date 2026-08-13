"""Button platform for the qBittorrent integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import QBittorrentConfigEntry, QBittorrentCoordinator
from .entity import QBittorrentEntity


@dataclass(frozen=True, kw_only=True)
class QBittorrentButtonEntityDescription(ButtonEntityDescription):
    """Describes a qBittorrent button entity."""

    press_fn: Callable[[Any], None]


BUTTON_DESCRIPTIONS: tuple[QBittorrentButtonEntityDescription, ...] = (
    QBittorrentButtonEntityDescription(
        key="resume_all",
        translation_key="resume_all",
        icon="mdi:play",
        press_fn=lambda client: client.torrents_resume(torrent_hashes="all"),
    ),
    QBittorrentButtonEntityDescription(
        key="pause_all",
        translation_key="pause_all",
        icon="mdi:pause",
        press_fn=lambda client: client.torrents_pause(torrent_hashes="all"),
    ),
    QBittorrentButtonEntityDescription(
        key="reannounce_all",
        translation_key="reannounce_all",
        icon="mdi:bullhorn-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_fn=lambda client: client.torrents_reannounce(torrent_hashes="all"),
    ),
    QBittorrentButtonEntityDescription(
        key="shutdown",
        translation_key="shutdown",
        icon="mdi:power",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_fn=lambda client: client.app_shutdown(),
    ),
)


class QBittorrentButton(QBittorrentEntity, ButtonEntity):
    """Representation of a global qBittorrent action button."""

    entity_description: QBittorrentButtonEntityDescription

    def __init__(
        self,
        coordinator: QBittorrentCoordinator,
        description: QBittorrentButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.hass.async_add_executor_job(
            self.entity_description.press_fn, self.coordinator.client
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: QBittorrentConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up qBittorrent buttons from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        QBittorrentButton(coordinator, description) for description in BUTTON_DESCRIPTIONS
    )
