"""Tests for qBittorrent diagnostics redaction."""

from __future__ import annotations

from custom_components.qbt.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redacts_secrets(hass, mock_config_entry):
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["entry"]["password"] == "**REDACTED**"
    assert diagnostics["entry"]["username"] == "**REDACTED**"
    assert diagnostics["entry"]["host"] == "**REDACTED**"
    assert diagnostics["app_version"] == "v5.2.3"
    assert diagnostics["torrent_count"] == 2
