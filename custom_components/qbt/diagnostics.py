"""Diagnostics support for the qBittorrent integration."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import QBittorrentConfigEntry

TO_REDACT_ENTRY = {"username", "password", "api_key", "host"}
TO_REDACT_PREFERENCES = {
    "web_ui_username",
    "web_ui_password",
    "web_ui_password_hash",
    "proxy_username",
    "proxy_password",
    "bypass_auth_subnet_whitelist",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: QBittorrentConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    try:
        library_version = pkg_version("qbittorrent-api")
    except PackageNotFoundError:
        library_version = "unknown"

    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT_ENTRY),
        "options": dict(entry.options),
        "qbittorrent_api_library_version": library_version,
        "last_update_success": coordinator.last_update_success,
        "app_version": data.app_version,
        "web_api_version": data.web_api_version,
        "build_info": dict(data.build_info),
        "preferences": async_redact_data(dict(data.preferences), TO_REDACT_PREFERENCES),
        "server_state": data.server_state,
        "torrent_count": len(data.torrents),
        "categories": data.categories,
        "tags": data.tags,
    }
