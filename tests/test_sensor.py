"""Tests for qBittorrent sensors."""

from __future__ import annotations

from homeassistant.helpers import entity_registry as er


async def test_global_sensors_populated(hass, mock_config_entry):
    # Fetch by unique_id via the entity registry to stay independent of the
    # exact entity_id slugification.
    registry = er.async_get(hass)

    entry_id = mock_config_entry.entry_id
    entity_id = registry.async_get_entity_id("sensor", "qbt", f"{entry_id}_dl_speed")
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    # The entity reports in its suggested display unit (MB/s), not the native B/s.
    assert float(state.state) == 500 / 1_000_000
    assert state.attributes["unit_of_measurement"] == "MB/s"


async def test_torrent_count_sensor(hass, mock_config_entry):
    registry = er.async_get(hass)
    entry_id = mock_config_entry.entry_id
    entity_id = registry.async_get_entity_id("sensor", "qbt", f"{entry_id}_torrents_total")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state.state == "2"
