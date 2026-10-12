"""Tests for the decoded entities: relays, grid power, Data 13, battery (spec.md 6b)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.solax_adapter_box_g2.const import DOMAIN

from .conftest import SERIAL

# Clock, relays DO1-DO4 = 1, 1, 0, 0, AO, 11, grid -2300, Data 13, SOC, 15-17.
DATA = [9, 42, 22, 11, 10, 26, 1, 1, 0, 0, 0, 1, -2300, -2047, 75, 1, 0, 1]


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{SERIAL}_{key}")
    assert entity_id is not None, key
    return entity_id


@pytest.fixture(autouse=True)
def decoded_data(mock_client: AsyncMock) -> None:
    """Use an answer with two closed relays and negative powers."""
    mock_client.read_realtime.return_value["Data"] = list(DATA)


async def test_relays(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Relay DO1-DO4 follow Data[6..9] (spec.md 6b)."""
    await _setup(hass, config_entry)

    states = [hass.states.get(_entity_id(hass, "binary_sensor", f"relay_do{n}")) for n in range(1, 5)]
    assert [state.state for state in states] == [STATE_ON, STATE_ON, STATE_OFF, STATE_OFF]
    assert states[0].name == "Adapter Box G2 Relay DO1"
    assert states[3].name == "Adapter Box G2 Relay DO4"


async def test_active_relays(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Active relays counts the closed relays (spec.md 6b)."""
    await _setup(hass, config_entry)

    state = hass.states.get(_entity_id(hass, "sensor", "active_relays"))
    assert state.state == "2"
    assert state.name == "Adapter Box G2 Active relays"
    assert state.attributes["state_class"] == "measurement"


@pytest.mark.parametrize(
    ("key", "name", "value", "unit", "device_class"),
    [
        ("grid_power", "Grid power", "-2300", "W", "power"),
        ("data13_power", "Data 13 power", "-2047", "W", "power"),
        ("battery_soc", "Battery", "75", "%", "battery"),
    ],
)
async def test_power_and_battery(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    config_entry: MockConfigEntry,
    key: str,
    name: str,
    value: str,
    unit: str,
    device_class: str,
) -> None:
    """Grid power, Data 13 power and battery with unit and class (spec.md 6b)."""
    await _setup(hass, config_entry)

    state = hass.states.get(_entity_id(hass, "sensor", key))
    assert state.state == value
    assert state.name == f"Adapter Box G2 {name}"
    assert state.attributes["unit_of_measurement"] == unit
    assert state.attributes["device_class"] == device_class
    assert state.attributes["state_class"] == "measurement"


async def test_unavailable_when_position_missing(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """A shorter Data array makes the decoded entities unavailable (spec.md 6b)."""
    await _setup(hass, config_entry)

    mock_client.read_realtime.return_value = {
        **mock_client.read_realtime.return_value,
        "Data": DATA[:8],
    }
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
    await hass.async_block_till_done()

    assert hass.states.get(_entity_id(hass, "binary_sensor", "relay_do1")).state == STATE_ON
    assert hass.states.get(_entity_id(hass, "binary_sensor", "relay_do3")).state == STATE_UNAVAILABLE
    for key in ("active_relays", "grid_power", "data13_power", "battery_soc"):
        assert hass.states.get(_entity_id(hass, "sensor", key)).state == STATE_UNAVAILABLE


async def test_german_names(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The decoded entities have German names (spec.md 6b)."""
    hass.config.language = "de"
    await _setup(hass, config_entry)

    assert hass.states.get(_entity_id(hass, "binary_sensor", "relay_do2")).name == (
        "Adapter Box G2 Relais DO2"
    )
    assert hass.states.get(_entity_id(hass, "sensor", "active_relays")).name == (
        "Adapter Box G2 Aktive Relais"
    )
    assert hass.states.get(_entity_id(hass, "sensor", "grid_power")).name == (
        "Adapter Box G2 Netzleistung"
    )
    assert hass.states.get(_entity_id(hass, "sensor", "battery_soc")).name == (
        "Adapter Box G2 Akku-Ladestand"
    )
