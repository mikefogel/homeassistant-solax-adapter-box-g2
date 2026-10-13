"""Tests for setup, raw value sensors and decoded sensors (spec.md 5, 6)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.solax_adapter_box_g2.api import CannotConnect, InvalidResponse
from custom_components.solax_adapter_box_g2.const import DOMAIN
from custom_components.solax_adapter_box_g2.sensor import device_time, raw_attributes

from .conftest import SERIAL


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _next_poll(hass: HomeAssistant) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
    await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_{key}")
    assert entity_id is not None, key
    return entity_id


async def test_device_is_created(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """One device with serial number and firmware (spec.md 6)."""
    await _setup(hass, config_entry)

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), config_entry.entry_id)
    assert len(devices) == 1
    device = devices[0]
    assert device.identifiers == {(DOMAIN, SERIAL)}
    assert device.manufacturer == "SolaX Power"
    assert device.model == "Adapter Box G2"
    assert device.sw_version == "008.00"
    assert device.serial_number == SERIAL


async def test_one_sensor_per_unknown_data_index(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Undecoded Data positions get a raw sensor named after the index (spec.md 6a)."""
    await _setup(hass, config_entry)

    for index in (10, 11, 15, 16, 17):
        assert hass.states.get(_entity_id(hass, f"data_{index:02d}")) is not None

    state = hass.states.get(_entity_id(hass, "data_11"))
    assert state.state == "1"
    assert state.name == "Adapter Box G2 Data 11"
    assert state.attributes["state_class"] == "measurement"
    assert state.attributes["int16"] == 1
    assert state.attributes["bits"] == "0000000000000001"


async def test_no_raw_sensor_for_decoded_positions(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Decoded positions are shown by their decoded entities only (spec.md 6a)."""
    await _setup(hass, config_entry)
    registry = er.async_get(hass)

    for index in (*range(10), 12, 13, 14):
        assert (
            registry.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_data_{index:02d}")
            is None
        ), index


async def test_old_raw_sensors_of_decoded_positions_are_removed(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Raw sensors from earlier versions are removed from the registry (spec.md 6a)."""
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    for key in ("data_00", "data_06", "data_14", "data_15"):
        registry.async_get_or_create(
            "sensor", DOMAIN, f"{SERIAL}_{key}", config_entry=config_entry
        )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    for key in ("data_00", "data_06", "data_14"):
        assert registry.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_{key}") is None
    assert hass.states.get(_entity_id(hass, "data_15")).state == "1"


async def test_information_array_gets_sensors(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    config_entry: MockConfigEntry,
) -> None:
    """`Information` is recorded like `Data`; text values have no state class."""
    mock_client.read_realtime.return_value["Information"] = [5.0, "SDXXXXXXXX"]
    await _setup(hass, config_entry)

    assert hass.states.get(_entity_id(hass, "info_00")).state == "5.0"
    text = hass.states.get(_entity_id(hass, "info_01"))
    assert "state_class" not in text.attributes
    assert "int16" not in text.attributes


async def test_settings_get_sensors_when_supported(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """ReadSetData values become `Setting xx` sensors (spec.md 6a)."""
    mock_client.read_settings.side_effect = None
    mock_client.read_settings.return_value = {"Data": [3, 65535]}
    await _setup(hass, config_entry)

    state = hass.states.get(_entity_id(hass, "set_01"))
    assert state.name == "Adapter Box G2 Setting 01"
    assert state.state == "65535"
    assert state.attributes["int16"] == -1


async def test_top_level_and_device_time(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """`type`, `devKind` and the decoded clock (spec.md 6a, 6b)."""
    await _setup(hass, config_entry)

    assert hass.states.get(_entity_id(hass, "device_kind")).state == "8"
    assert hass.states.get(_entity_id(hass, "device_type")).state == "0"
    expected = device_time([9, 42, 22, 11, 10, 26])
    assert expected is not None
    assert hass.states.get(_entity_id(hass, "device_time")).state == expected.astimezone(
        dt_util.UTC
    ).isoformat(timespec="seconds")
    assert (expected.year, expected.month, expected.day, expected.hour) == (2026, 10, 11, 9)


def test_device_time_rejects_invalid_values() -> None:
    """Values that are not a date give no time (spec.md 6b)."""
    assert device_time([25, 0, 0, 1, 1, 26]) is None
    assert device_time([1, 2]) is None
    assert device_time(["x", 0, 0, 1, 1, 26]) is None


def test_raw_attributes() -> None:
    """Only integers 0-65535 get int16 and bits (spec.md 6a)."""
    assert raw_attributes(40000) == {"int16": -25536, "bits": "1001110001000000"}
    assert raw_attributes(-1) is None
    assert raw_attributes(70000) is None
    assert raw_attributes(1.5) is None
    assert raw_attributes(True) is None


async def test_longer_array_adds_sensors(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """New indices get sensors without a reload; missing ones become unavailable."""
    await _setup(hass, config_entry)
    data = mock_client.read_realtime.return_value["Data"]

    mock_client.read_realtime.return_value = {
        **mock_client.read_realtime.return_value,
        "Data": [*data, 7],
    }
    await _next_poll(hass)
    assert hass.states.get(_entity_id(hass, "data_18")).state == "7"

    mock_client.read_realtime.return_value = {
        **mock_client.read_realtime.return_value,
        "Data": data[:17],
    }
    await _next_poll(hass)
    assert hass.states.get(_entity_id(hass, "data_17")).state == STATE_UNAVAILABLE
    assert hass.states.get(_entity_id(hass, "data_18")).state == STATE_UNAVAILABLE


async def test_connection_loss_and_recovery(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Entities become unavailable and recover by themselves (spec.md 5)."""
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, "battery_soc")

    mock_client.read_realtime.side_effect = CannotConnect("down")
    await _next_poll(hass)
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    mock_client.read_realtime.side_effect = None
    await _next_poll(hass)
    assert hass.states.get(entity_id).state == "75"


@pytest.mark.parametrize(
    ("error", "key"),
    [(CannotConnect("down"), "cannot_connect"), (InvalidResponse("y"), "invalid_response")],
)
async def test_polling_errors_are_translated(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    config_entry: MockConfigEntry,
    error: Exception,
    key: str,
) -> None:
    """A failed poll carries a translation key, not the raw error text (spec.md 8)."""
    await _setup(hass, config_entry)

    mock_client.read_realtime.side_effect = error
    await _next_poll(hass)

    exc = config_entry.runtime_data.last_exception
    assert exc.translation_domain == DOMAIN
    assert exc.translation_key == key
    assert str(error) not in str(exc)


async def test_unreachable_at_startup_retries(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Setup is retried by Home Assistant (spec.md 5)."""
    mock_client.read_realtime.side_effect = CannotConnect("down")
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The entry unloads cleanly."""
    await _setup(hass, config_entry)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
