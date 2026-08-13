"""Tests for qBittorrent switch entities."""

from __future__ import annotations

from homeassistant.helpers import entity_registry as er


async def _entity_id(hass, entry_id: str, key: str) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", "qbt", f"{entry_id}_{key}")
    assert entity_id is not None
    return entity_id


async def test_queueing_enabled_reflects_preferences(hass, mock_config_entry):
    entity_id = await _entity_id(hass, mock_config_entry.entry_id, "queueing_enabled")
    state = hass.states.get(entity_id)
    assert state.state == "on"


async def test_turning_off_queueing_forces_immediate_refresh(hass, mock_config_entry):
    """A switch backed by preferences must not wait for the next slow cycle."""
    client = mock_config_entry.runtime_data.client
    entity_id = await _entity_id(hass, mock_config_entry.entry_id, "queueing_enabled")

    def fake_set_preferences(prefs):
        client.app_preferences.return_value = {
            **client.app_preferences.return_value,
            **prefs,
        }

    client.app_set_preferences.side_effect = fake_set_preferences

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )

    client.app_set_preferences.assert_called_once_with({"queueing_enabled": False})
    state = hass.states.get(entity_id)
    assert state.state == "off"
