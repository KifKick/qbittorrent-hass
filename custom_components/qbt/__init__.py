"""The qBittorrent integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .coordinator import QBittorrentConfigEntry, QBittorrentCoordinator
from .services import async_setup_services

# This integration is config-flow only; it has never supported (and does not
# support) YAML configuration.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the qBittorrent component-level services."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: QBittorrentConfigEntry) -> bool:
    """Set up a qBittorrent config entry."""
    coordinator = QBittorrentCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: QBittorrentConfigEntry) -> bool:
    """Unload a qBittorrent config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: QBittorrentConfigEntry) -> None:
    """Reload the entry when options change (e.g. scan interval, feature toggles)."""
    await hass.config_entries.async_reload(entry.entry_id)
