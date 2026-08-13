"""DataUpdateCoordinator for the qBittorrent integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from qbittorrentapi import Client
from qbittorrentapi.exceptions import (
    APIConnectionError,
    Forbidden403Error,
    LoginFailed,
    UnsupportedQbittorrentVersion,
)

from .const import (
    AUTH_METHOD_API_KEY,
    CONF_API_KEY,
    CONF_AUTH_METHOD,
    CONF_PATH,
    CONF_SCAN_INTERVAL,
    CONF_USE_HTTPS,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLOW_UPDATE_EVERY_N_CYCLES,
    DOMAIN,
    STATES_CHECKING,
    STATES_DOWNLOADING,
    STATES_ERRORED,
    STATES_PAUSED,
    STATES_SEEDING,
)

_LOGGER = logging.getLogger(__name__)

type QBittorrentConfigEntry = ConfigEntry[QBittorrentCoordinator]


@dataclass
class QBittorrentData:
    """Snapshot of qBittorrent state used to populate entities."""

    server_state: dict[str, Any] = field(default_factory=dict)
    torrents: dict[str, dict[str, Any]] = field(default_factory=dict)
    categories: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    counts_by_state: dict[str, int] = field(default_factory=dict)
    app_version: str | None = None
    web_api_version: str | None = None
    build_info: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    default_save_path: str | None = None


def build_client(entry_data: dict[str, Any]) -> Client:
    """Build a qbittorrent-api Client from config entry data.

    Isolated in one place so the API-key vs. username/password branching
    (and the exact Client kwarg for each) only needs to be maintained here.
    """
    host = entry_data[CONF_USE_HTTPS] and "https://" or "http://"
    host += entry_data["host"]
    if path := entry_data.get(CONF_PATH):
        host = f"{host}/{path.strip('/')}"

    kwargs: dict[str, Any] = {
        "host": host,
        "port": entry_data["port"],
        "VERIFY_WEBUI_CERTIFICATE": entry_data.get(CONF_VERIFY_SSL, True),
        "FORCE_SCHEME_FROM_HOST": True,
        "REQUESTS_ARGS": {"timeout": 15},
    }
    if entry_data.get(CONF_AUTH_METHOD) == AUTH_METHOD_API_KEY:
        kwargs["api_key"] = entry_data[CONF_API_KEY]
    else:
        kwargs["username"] = entry_data.get("username")
        kwargs["password"] = entry_data.get("password")

    return Client(**kwargs)


class QBittorrentCoordinator(DataUpdateCoordinator[QBittorrentData]):
    """Coordinates polling of a qBittorrent instance."""

    config_entry: QBittorrentConfigEntry

    def __init__(self, hass: HomeAssistant, entry: QBittorrentConfigEntry) -> None:
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = build_client(entry.data)
        self._rid: int = 0
        self._server_state: dict[str, Any] = {}
        self._torrents: dict[str, dict[str, Any]] = {}
        self._categories: dict[str, Any] = {}
        self._tags: set[str] = set()
        self._cycle = 0
        self._force_next_preferences_fetch = False
        self._unsupported_version_notified = False

    async def async_request_refresh_after_write(self) -> None:
        """Refresh after a switch/number/button write.

        Preferences are normally only re-fetched every Nth cycle; forcing a
        fetch on the very next cycle means an entity backed by
        ``data.preferences`` reflects the value the user just set immediately,
        instead of waiting for the next slow cycle.
        """
        self._force_next_preferences_fetch = True
        await self.async_request_refresh()

    async def _async_update_data(self) -> QBittorrentData:
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except LoginFailed as err:
            raise ConfigEntryAuthFailed("qBittorrent authentication failed") from err
        except Forbidden403Error as err:
            raise ConfigEntryAuthFailed("qBittorrent session was rejected") from err
        except UnsupportedQbittorrentVersion as err:
            self._notify_unsupported_version(err)
            raise UpdateFailed(f"Unsupported qBittorrent version: {err}") from err
        except APIConnectionError as err:
            raise UpdateFailed(f"Cannot connect to qBittorrent: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error communicating with qBittorrent: {err}") from err

    def _notify_unsupported_version(self, err: Exception) -> None:
        if self._unsupported_version_notified:
            return
        self._unsupported_version_notified = True
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            f"unsupported_version_{self.config_entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="unsupported_version",
            translation_placeholders={"error": str(err)},
        )

    def _fetch(self) -> QBittorrentData:
        """Fetch data from qBittorrent. Runs in an executor thread."""
        maindata = self.client.sync_maindata(rid=self._rid)
        self._rid = maindata.get("rid", self._rid)

        # Like torrents/categories/tags, server_state is also subject to the
        # rid-based diffing: once full_update is no longer True, qBittorrent
        # only includes the fields that changed since the last poll. Merging
        # into a persistent cache (instead of replacing it wholesale) keeps
        # unchanged fields (e.g. connection_status, dl_info_speed) from
        # disappearing as soon as they stop changing between polls.
        self._server_state.update(maindata.get("server_state", {}))

        if maindata.get("full_update"):
            self._torrents = dict(maindata.get("torrents", {}))
        else:
            for torrent_hash, changes in maindata.get("torrents", {}).items():
                self._torrents.setdefault(torrent_hash, {}).update(changes)
            for torrent_hash in maindata.get("torrents_removed", []):
                self._torrents.pop(torrent_hash, None)

        self._categories.update(maindata.get("categories", {}))
        for name in maindata.get("categories_removed", []):
            self._categories.pop(name, None)

        self._tags.update(maindata.get("tags", []))
        for name in maindata.get("tags_removed", []):
            self._tags.discard(name)

        counts_by_state = self._aggregate_counts(self._torrents)

        data = QBittorrentData(
            server_state=dict(self._server_state),
            torrents=dict(self._torrents),
            categories=dict(self._categories),
            tags=sorted(self._tags),
            counts_by_state=counts_by_state,
            app_version=self.data.app_version if self.data else None,
            web_api_version=self.data.web_api_version if self.data else None,
            build_info=self.data.build_info if self.data else {},
            preferences=self.data.preferences if self.data else {},
            default_save_path=self.data.default_save_path if self.data else None,
        )

        is_slow_cycle = self._cycle % DEFAULT_SLOW_UPDATE_EVERY_N_CYCLES == 0
        if is_slow_cycle or self._force_next_preferences_fetch:
            data.app_version = self.client.app_version()
            data.web_api_version = self.client.app_web_api_version()
            data.build_info = dict(self.client.app_build_info())
            data.preferences = dict(self.client.app_preferences())
            data.default_save_path = self.client.app_default_save_path()
            self._force_next_preferences_fetch = False
        self._cycle += 1

        return data

    @staticmethod
    def _aggregate_counts(torrents: dict[str, dict[str, Any]]) -> dict[str, int]:
        counts = {
            "total": len(torrents),
            "downloading": 0,
            "seeding": 0,
            "paused": 0,
            "checking": 0,
            "error": 0,
        }
        for torrent in torrents.values():
            state = torrent.get("state")
            if state in STATES_DOWNLOADING:
                counts["downloading"] += 1
            elif state in STATES_SEEDING:
                counts["seeding"] += 1
            elif state in STATES_PAUSED:
                counts["paused"] += 1
            elif state in STATES_CHECKING:
                counts["checking"] += 1
            elif state in STATES_ERRORED:
                counts["error"] += 1
        return counts
