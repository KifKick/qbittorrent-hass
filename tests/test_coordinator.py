"""Tests for the qBittorrent DataUpdateCoordinator."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.helpers import issue_registry as ir
from qbittorrentapi.exceptions import APIConnectionError, Forbidden403Error, LoginFailed

from custom_components.qbt.const import DOMAIN
from custom_components.qbt.coordinator import QBittorrentCoordinator

from .conftest import MOCK_SERVER_STATE


async def test_initial_full_update_populates_data(hass, mock_config_entry):
    """After first refresh, all torrents/categories/tags/counts should be present."""
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data

    assert coordinator.data.app_version == "v5.2.3"
    assert coordinator.data.web_api_version == "2.15.1"
    assert len(coordinator.data.torrents) == 2
    assert coordinator.data.categories == {"linux": {"savePath": "/downloads/linux"}}
    assert coordinator.data.tags == ["important"]
    assert coordinator.data.counts_by_state["total"] == 2
    assert coordinator.data.counts_by_state["downloading"] == 1
    assert coordinator.data.counts_by_state["seeding"] == 1


async def test_incremental_update_merges_and_removes(hass, mock_config_entry):
    """A delta sync_maindata payload should merge changes and drop removed torrents."""
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    client = coordinator.client

    client.sync_maindata.return_value = {
        "rid": 2,
        "full_update": False,
        "torrents": {"hash1": {"progress": 0.75, "state": "uploading"}},
        "torrents_removed": ["hash2"],
        "categories": {},
        "categories_removed": [],
        "tags": [],
        "tags_removed": ["important"],
        "server_state": {**MOCK_SERVER_STATE, "dl_info_speed": 0},
    }

    await coordinator.async_refresh()

    assert len(coordinator.data.torrents) == 1
    assert "hash2" not in coordinator.data.torrents
    assert coordinator.data.torrents["hash1"]["progress"] == 0.75
    assert coordinator.data.torrents["hash1"]["name"] == "Ubuntu ISO"  # preserved from full update
    assert coordinator.data.tags == []
    assert coordinator.data.counts_by_state["seeding"] == 1
    assert coordinator.data.counts_by_state["downloading"] == 0
    assert coordinator.data.server_state["dl_info_speed"] == 0


async def test_partial_server_state_delta_preserves_unchanged_fields(hass, mock_config_entry):
    """qBittorrent only sends changed server_state fields once full_update is False.

    Fields absent from a delta must not disappear from coordinator.data.server_state;
    they should keep their last known value until qBittorrent reports a change.
    """
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    client = coordinator.client

    client.sync_maindata.return_value = {
        "rid": 2,
        "full_update": False,
        "torrents": {},
        "torrents_removed": [],
        "categories": {},
        "categories_removed": [],
        "tags": [],
        "tags_removed": [],
        # Only this one field changed; qBittorrent omits everything else.
        "server_state": {"up_info_data": 999},
    }

    await coordinator.async_refresh()

    assert coordinator.data.server_state["up_info_data"] == 999
    # Untouched fields must be carried over from the initial full update.
    assert coordinator.data.server_state["connection_status"] == "connected"
    assert coordinator.data.server_state["dl_info_speed"] == 500


async def test_login_failed_marks_update_unsuccessful_and_triggers_reauth(hass, mock_config_entry):
    """LoginFailed means the retried internal re-login itself failed: credentials are bad."""
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    coordinator.client.sync_maindata.side_effect = LoginFailed()

    with patch.object(coordinator.config_entry, "async_start_reauth") as start_reauth:
        await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    start_reauth.assert_called_once()


async def test_connection_error_marks_update_failed(hass, mock_config_entry):
    """A connection error should mark the update as failed without raising."""
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    coordinator.client.sync_maindata.side_effect = APIConnectionError("boom")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_forbidden_403_fails_update_without_forcing_reauth(hass, mock_config_entry):
    """A bare 403 only surfaces after qbittorrent-api's own re-login retry succeeded
    (see Request._auth_request), so credentials are fine (e.g. a brute-force IP ban
    instead). It should not force the user through a reauth flow.
    """
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    coordinator.client.sync_maindata.side_effect = Forbidden403Error()

    with patch.object(coordinator.config_entry, "async_start_reauth") as start_reauth:
        await coordinator.async_refresh()

    assert coordinator.last_update_success is False
    start_reauth.assert_not_called()


async def test_slow_cycle_failure_does_not_fail_whole_update(hass, mock_config_entry):
    """A transient failure fetching app_version/preferences (the rarely-polled 'slow
    cycle') must not take down torrent/speed data that already updated fine this cycle.
    """
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    client = coordinator.client

    coordinator._force_next_preferences_fetch = True
    client.app_version.side_effect = APIConnectionError("boom")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert len(coordinator.data.torrents) == 2
    assert coordinator.data.app_version == "v5.2.3"  # stale value preserved, not cleared
    assert coordinator._force_next_preferences_fetch is True  # retried on the next cycle


async def test_unsupported_version_warns_without_failing_updates(hass, mock_config_entry):
    """An unsupported qBittorrent version must only create a repair issue, not ever
    fail updates (the coordinator's client intentionally never sets
    RAISE_ERROR_FOR_UNSUPPORTED_QBITTORRENT_VERSIONS, unlike the config flow's).
    """
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    client = coordinator.client
    client.app_version.return_value = "v0.1.0"
    client.app_web_api_version.return_value = "0.1"
    coordinator._force_next_preferences_fetch = True

    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    registry = ir.async_get(hass)
    issue = registry.async_get_issue(
        DOMAIN, f"unsupported_version_{coordinator.config_entry.entry_id}"
    )
    assert issue is not None
