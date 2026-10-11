"""Tests for ReadSetData handling, the change log and diagnostics (spec.md 3e, 7)."""

from __future__ import annotations

from datetime import timedelta
import json
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.solax_adapter_box_g2.api import CannotConnect
from custom_components.solax_adapter_box_g2.const import SETTINGS_POLL_EVERY
from custom_components.solax_adapter_box_g2.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import SERIAL


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _polls(hass: HomeAssistant, count: int) -> None:
    for _ in range(count):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=11))
        await hass.async_block_till_done()


async def test_unsupported_settings_are_asked_once(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """A non-JSON answer to ReadSetData stops further requests (spec.md 3e)."""
    await _setup(hass, config_entry)
    await _polls(hass, 2 * SETTINGS_POLL_EVERY)

    assert mock_client.read_settings.call_count == 1
    assert config_entry.runtime_data.settings_supported is False


async def test_supported_settings_are_polled_every_nth_cycle(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """ReadSetData is sent in every n-th cycle only (spec.md 3e)."""
    mock_client.read_settings.side_effect = None
    mock_client.read_settings.return_value = {"Data": [1]}
    await _setup(hass, config_entry)
    await _polls(hass, 2 * SETTINGS_POLL_EVERY)

    assert mock_client.read_realtime.call_count == 2 * SETTINGS_POLL_EVERY + 1
    assert mock_client.read_settings.call_count == 3
    assert config_entry.runtime_data.settings_supported is True


async def test_connection_error_on_settings_keeps_asking(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """A connection error says nothing about support (spec.md 3e)."""
    mock_client.read_settings.side_effect = CannotConnect("down")
    await _setup(hass, config_entry)
    await _polls(hass, SETTINGS_POLL_EVERY)

    assert mock_client.read_settings.call_count == 2
    assert config_entry.runtime_data.settings_supported is None


async def test_change_log_records_changes_but_not_the_clock(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Changed values are logged with old and new value (spec.md 7)."""
    await _setup(hass, config_entry)
    answer = mock_client.read_realtime.return_value
    data = list(answer["Data"])
    data[2] = 32  # clock second: not logged
    data[6] = 1  # suspected dry contact DO1
    mock_client.read_realtime.return_value = {**answer, "Data": data, "ver": "009.00"}

    await _polls(hass, 1)

    log = list(config_entry.runtime_data.change_log)
    assert [(e["value"], e["old"], e["new"]) for e in log] == [
        ("ver", "008.00", "009.00"),
        ("data_06", 0, 1),
    ]
    assert dt_util.parse_datetime(log[0]["time"]) is not None


async def test_diagnostics_are_redacted(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Raw answers and change log without serial number or password (spec.md 7)."""
    await _setup(hass, config_entry)

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["realtime"]["Data"][13] == 409
    assert diagnostics["settings_supported"] is False
    assert diagnostics["change_log"] == []
    assert SERIAL not in json.dumps(diagnostics)
