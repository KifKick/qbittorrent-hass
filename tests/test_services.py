"""Tests for the qBittorrent services."""

from __future__ import annotations

import pytest
from homeassistant.exceptions import ServiceValidationError
from qbittorrentapi.exceptions import Conflict409Error, NotFound404Error

from custom_components.qbt.const import DOMAIN


async def test_pause_torrents_calls_client(hass, mock_config_entry):
    client = mock_config_entry.runtime_data.client

    await hass.services.async_call(
        DOMAIN,
        "pause_torrents",
        {"config_entry_id": mock_config_entry.entry_id, "hashes": ["hash1", "hash2"]},
        blocking=True,
    )

    client.torrents_pause.assert_called_once_with(torrent_hashes=["hash1", "hash2"])


async def test_delete_torrents_passes_delete_files(hass, mock_config_entry):
    client = mock_config_entry.runtime_data.client

    await hass.services.async_call(
        DOMAIN,
        "delete_torrents",
        {
            "config_entry_id": mock_config_entry.entry_id,
            "hashes": ["hash1"],
            "delete_files": True,
        },
        blocking=True,
    )

    client.torrents_delete.assert_called_once_with(
        torrent_hashes=["hash1"], delete_files=True
    )


async def test_add_torrent_with_urls(hass, mock_config_entry):
    client = mock_config_entry.runtime_data.client
    client.torrents_add.return_value = "Ok."

    await hass.services.async_call(
        DOMAIN,
        "add_torrent",
        {
            "config_entry_id": mock_config_entry.entry_id,
            "urls": ["magnet:?xt=urn:btih:deadbeef"],
            "category": "linux",
        },
        blocking=True,
    )

    assert client.torrents_add.call_count == 1
    _, kwargs = client.torrents_add.call_args
    assert kwargs["urls"] == ["magnet:?xt=urn:btih:deadbeef"]
    assert kwargs["category"] == "linux"


async def test_add_torrent_requires_a_source(hass, mock_config_entry):
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "add_torrent",
            {"config_entry_id": mock_config_entry.entry_id},
            blocking=True,
        )


async def test_get_torrents_returns_response(hass, mock_config_entry):
    client = mock_config_entry.runtime_data.client
    client.torrents_info.return_value = [
        {"hash": "hash1", "name": "Ubuntu ISO", "state": "downloading"}
    ]

    response = await hass.services.async_call(
        DOMAIN,
        "get_torrents",
        {"config_entry_id": mock_config_entry.entry_id},
        blocking=True,
        return_response=True,
    )

    assert response["torrents"] == [
        {"hash": "hash1", "name": "Ubuntu ISO", "state": "downloading"}
    ]


async def test_conflict_error_raises_service_validation_error(hass, mock_config_entry):
    client = mock_config_entry.runtime_data.client
    client.torrents_set_category.side_effect = Conflict409Error()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "set_category",
            {
                "config_entry_id": mock_config_entry.entry_id,
                "hashes": ["hash1"],
                "category": "does-not-exist",
            },
            blocking=True,
        )


async def test_not_found_error_raises_service_validation_error(hass, mock_config_entry):
    client = mock_config_entry.runtime_data.client
    client.torrents_rename.side_effect = NotFound404Error()

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "rename_torrent",
            {
                "config_entry_id": mock_config_entry.entry_id,
                "hash": "unknown",
                "name": "New name",
            },
            blocking=True,
        )


async def test_unknown_config_entry_raises(hass, mock_config_entry):
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "pause_torrents",
            {"config_entry_id": "does-not-exist", "hashes": ["hash1"]},
            blocking=True,
        )
