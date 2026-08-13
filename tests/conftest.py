"""Fixtures for qBittorrent integration tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.qbittorrent.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

MOCK_CONFIG_DATA = {
    "host": "192.168.1.10",
    "port": 8080,
    "use_https": False,
    "verify_ssl": True,
    "path": "",
    "auth_method": "password",
    "username": "admin",
    "password": "adminadmin",
}

MOCK_SERVER_STATE = {
    "dl_info_speed": 500,
    "up_info_speed": 100,
    "dl_info_data": 123456,
    "up_info_data": 65432,
    "dl_rate_limit": 0,
    "up_rate_limit": 0,
    "global_ratio": "1.5",
    "free_space_on_disk": 999999999,
    "dht_nodes": 10,
    "total_peer_connections": 5,
    "connection_status": "connected",
    "use_alt_speed_limits": False,
}

MOCK_MAINDATA_FULL = {
    "rid": 1,
    "full_update": True,
    "torrents": {
        "hash1": {
            "name": "Ubuntu ISO",
            "state": "downloading",
            "progress": 0.5,
            "category": "linux",
            "tags": "",
            "save_path": "/downloads",
            "ratio": 0.0,
            "size": 1000,
            "eta": 100,
            "dlspeed": 500,
            "upspeed": 0,
        },
        "hash2": {
            "name": "Debian ISO",
            "state": "uploading",
            "progress": 1.0,
            "category": "",
            "tags": "",
            "save_path": "/downloads",
            "ratio": 2.0,
            "size": 2000,
            "eta": 0,
            "dlspeed": 0,
            "upspeed": 100,
        },
    },
    "categories": {"linux": {"savePath": "/downloads/linux"}},
    "tags": ["important"],
    "server_state": MOCK_SERVER_STATE,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration loading in every test."""
    yield


@pytest.fixture
def mock_qbt_client():
    """Return a MagicMock standing in for qbittorrentapi.Client."""
    client = MagicMock()
    client.auth_log_in.return_value = None
    client.app_version.return_value = "v5.2.3"
    client.app_web_api_version.return_value = "2.15.1"
    client.app_build_info.return_value = {"qt": "6.7.0"}
    client.app_preferences.return_value = {"dht": True}
    client.app_default_save_path.return_value = "/downloads"
    client.sync_maindata.return_value = dict(MOCK_MAINDATA_FULL)
    client.transfer_speed_limits_mode.return_value = "0"
    return client


@pytest.fixture
def mock_qbt_client_class(mock_qbt_client):
    """Patch the Client class used by the coordinator/config flow."""
    with patch(
        "custom_components.qbittorrent.coordinator.Client", return_value=mock_qbt_client
    ) as client_cls:
        yield client_cls


@pytest.fixture
async def mock_config_entry(hass, mock_qbt_client_class):
    """Create and set up a fully-loaded qBittorrent config entry."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_DATA, unique_id="192.168.1.10:8080")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
