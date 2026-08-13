"""Tests for the qBittorrent config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from qbittorrentapi.exceptions import APIConnectionError, Forbidden403Error, LoginFailed

from custom_components.qbt.const import CONF_SCAN_INTERVAL, DOMAIN

from .conftest import MOCK_CONFIG_DATA

USER_INPUT = {
    "host": "192.168.1.10",
    "port": 8080,
    "use_https": False,
    "verify_ssl": True,
    "path": "",
    "auth_method": "password",
}
AUTH_INPUT = {"username": "admin", "password": "adminadmin"}


async def _start_user_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_full_flow_success(hass, mock_qbt_client_class):
    """A complete user -> auth flow with valid credentials creates an entry."""
    result = await _start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], AUTH_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == "192.168.1.10"


async def test_invalid_auth_shows_error(hass, mock_qbt_client_class, mock_qbt_client):
    """LoginFailed during validation should surface as an invalid_auth form error."""
    mock_qbt_client.auth_log_in.side_effect = LoginFailed()

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], AUTH_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_banned_shows_distinct_error_from_invalid_auth(
    hass, mock_qbt_client_class, mock_qbt_client
):
    """Forbidden403Error (qBittorrent brute-force ban) must not look like wrong credentials."""
    mock_qbt_client.auth_log_in.side_effect = Forbidden403Error()

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "banned"}


async def test_cannot_connect_shows_error(hass, mock_qbt_client_class, mock_qbt_client):
    """A connection error during validation should surface as cannot_connect."""
    mock_qbt_client.auth_log_in.side_effect = APIConnectionError("unreachable")

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], AUTH_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_entry_aborts(hass, mock_qbt_client_class):
    """Configuring the same host:port twice should abort as already_configured."""
    existing = MockConfigEntry(
        domain=DOMAIN, data=MOCK_CONFIG_DATA, unique_id="192.168.1.10:8080"
    )
    existing.add_to_hass(hass)

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], AUTH_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_round_trip(hass, mock_config_entry):
    """The options flow should accept and persist new values."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: 60,
            "enable_torrent_list_sensor": False,
            "max_torrents_in_attributes": 50,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_SCAN_INTERVAL] == 60
