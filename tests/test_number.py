"""Tests for qBittorrent number entities."""

from __future__ import annotations

from homeassistant.helpers import entity_registry as er


async def _entity_id(hass, entry_id: str, key: str) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("number", "qbt", f"{entry_id}_{key}")
    assert entity_id is not None
    return entity_id


async def test_listen_port_shows_current_value(hass, mock_config_entry):
    entity_id = await _entity_id(hass, mock_config_entry.entry_id, "listen_port")
    state = hass.states.get(entity_id)
    assert state.state == "6881"


async def test_setting_dl_limit_calls_set_preferences_and_refreshes(hass, mock_config_entry):
    client = mock_config_entry.runtime_data.client
    entity_id = await _entity_id(hass, mock_config_entry.entry_id, "dl_limit")

    # Simulate qBittorrent actually applying the change on the next preferences fetch.
    def fake_set_preferences(prefs):
        client.app_preferences.return_value = {
            **client.app_preferences.return_value,
            **prefs,
        }

    client.app_set_preferences.side_effect = fake_set_preferences

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_id, "value": 512},
        blocking=True,
    )

    client.app_set_preferences.assert_called_once_with({"dl_limit": 512})
    state = hass.states.get(entity_id)
    assert state.state == "512"
