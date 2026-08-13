"""Tests for the qBittorrent DataUpdateCoordinator."""

from __future__ import annotations

from qbittorrentapi.exceptions import APIConnectionError, LoginFailed

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


async def test_login_failed_marks_update_unsuccessful(hass, mock_config_entry):
    """A LoginFailed error should be surfaced as a failed update (reauth trigger)."""
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    coordinator.client.sync_maindata.side_effect = LoginFailed()

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_connection_error_marks_update_failed(hass, mock_config_entry):
    """A connection error should mark the update as failed without raising."""
    coordinator: QBittorrentCoordinator = mock_config_entry.runtime_data
    coordinator.client.sync_maindata.side_effect = APIConnectionError("boom")

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
