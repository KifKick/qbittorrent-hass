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
from qbittorrentapi import Client, Version
from qbittorrentapi.exceptions import APIConnectionError, Forbidden403Error, LoginFailed

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


def build_client(entry_data: dict[str, Any], *, raise_for_unsupported_version: bool = False) -> Client:
    """Build a qbittorrent-api Client from config entry data.

    Isolated in one place so the API-key vs. username/password branching
    (and the exact Client kwarg for each) only needs to be maintained here.

    ``raise_for_unsupported_version`` is only meant for the short-lived client
    used to validate a connection in the config flow: it makes an unsupported
    version fail loudly *once*, as a one-time warning during setup/reauth. The
    coordinator's long-lived client must never set this, because a persistent
    client re-logs in automatically whenever its session expires (see
    ``Request._auth_request``) - if that flag were on there, every single
    re-login on an unsupported version would raise and permanently fail all
    updates, rather than just warning once and continuing.
    """
    host = "https://" if entry_data[CONF_USE_HTTPS] else "http://"
    host += entry_data["host"]
    if path := entry_data.get(CONF_PATH):
        host = f"{host}/{path.strip('/')}"

    kwargs: dict[str, Any] = {
        "host": host,
        "port": entry_data["port"],
        "VERIFY_WEBUI_CERTIFICATE": entry_data.get(CONF_VERIFY_SSL, True),
        "FORCE_SCHEME_FROM_HOST": True,
        "REQUESTS_ARGS": {"timeout": 15},
        "RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS": raise_for_unsupported_version,
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
            data = await self.hass.async_add_executor_job(self._fetch)
        except LoginFailed as err:
            # qbittorrent-api already retries once internally by re-logging in on a
            # 403 (see Request._auth_request); LoginFailed only reaches us once that
            # retry itself failed, so the stored credentials are genuinely bad.
            raise ConfigEntryAuthFailed("qBittorrent authentication failed") from err
        except Forbidden403Error as err:
            # Surfaces after the internal re-login retry *succeeded* but the request
            # still got a 403 (e.g. qBittorrent's brute-force IP ban). The stored
            # credentials aren't the problem, so don't force a reauth flow for it.
            _LOGGER.warning(
                "qBittorrent rejected a request with 403 despite valid credentials "
                "(possibly a temporary IP ban); will retry on the next update: %s", err
            )
            raise UpdateFailed(f"qBittorrent rejected the request: {err}") from err
        except APIConnectionError as err:
            raise UpdateFailed(f"Cannot connect to qBittorrent: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error communicating with qBittorrent: {err}") from err

        # Must run here (event loop), not inside self._fetch(): issue_registry isn't
        # thread-safe and self._fetch runs in the executor via async_add_executor_job.
        self._check_version_supported(data.app_version, data.web_api_version)
        return data

    async def async_close(self) -> None:
        """Log out of qBittorrent's WebUI session. Called on unload/reload.

        Best-effort: a logout failure (e.g. the session already expired, or the
        connection is currently down) must never block unload/reload.
        """
        try:
            await self.hass.async_add_executor_job(self.client.auth_log_out)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Ignoring error logging out of qBittorrent on unload: %s", err)

    def _check_version_supported(self, app_version: str | None, web_api_version: str | None) -> None:
        """Create a non-fixable repair issue if the version isn't fully supported.

        Per qbittorrent-api's own docs, an unsupported version still works for
        most methods, so this only warns once (via Repairs) instead of ever
        failing an update because of it.
        """
        if self._unsupported_version_notified or not app_version or not web_api_version:
            return
        if Version.is_app_version_supported(app_version) and Version.is_api_version_supported(
            web_api_version
        ):
            return
        self._unsupported_version_notified = True
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            f"unsupported_version_{self.config_entry.entry_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="unsupported_version",
            translation_placeholders={
                "error": f"App {app_version}, Web API {web_api_version}"
            },
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
            # Isolated from the maindata fetch above: a transient failure here
            # (rarely-called diagnostic endpoints) shouldn't take down torrent/speed
            # sensors that already updated fine this cycle. Keep the previous values
            # and let it try again next cycle.
            try:
                data.app_version = self.client.app_version()
                data.web_api_version = self.client.app_web_api_version()
                data.build_info = dict(self.client.app_build_info())
                data.preferences = dict(self.client.app_preferences())
                data.default_save_path = self.client.app_default_save_path()
                self._force_next_preferences_fetch = False
            except APIConnectionError as err:
                _LOGGER.warning("Failed to refresh qBittorrent app info/preferences: %s", err)
                self._force_next_preferences_fetch = True
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
