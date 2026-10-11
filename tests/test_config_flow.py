"""Tests for the config and options flow (spec.md 4)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solax_adapter_box_g2.api import CannotConnect, InvalidResponse
from custom_components.solax_adapter_box_g2.const import CONF_SCAN_INTERVAL, DOMAIN

from .conftest import HOST, SERIAL

USER_INPUT = {CONF_HOST: f"http://{HOST}/", CONF_PASSWORD: f" {SERIAL} "}


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """Host and password are tested and stored normalized (spec.md 4a)."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Adapter Box G2"
    assert result["data"] == {CONF_HOST: HOST, CONF_PASSWORD: SERIAL}
    assert result["result"].unique_id == SERIAL


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (CannotConnect("down"), "cannot_connect"),
        (InvalidResponse("not JSON"), "invalid_response"),
        (RuntimeError("boom"), "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant, mock_client: AsyncMock, error: Exception, expected: str
) -> None:
    """Errors are shown with translated keys and the form stays open."""
    mock_client.read_realtime.side_effect = error
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}


async def test_user_flow_without_serial_is_invalid(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """An answer without serial number cannot be set up."""
    mock_client.read_realtime.return_value = {"Data": [1]}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["errors"] == {"base": "invalid_response"}


async def test_same_box_aborts_and_updates_host(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The same serial number aborts and stores the new host (spec.md 4a)."""
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "192.168.0.99", CONF_PASSWORD: SERIAL}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data[CONF_HOST] == "192.168.0.99"


async def test_options_flow_sets_scan_interval(
    hass: HomeAssistant, mock_client: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The polling interval is stored as option (spec.md 4b)."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 30}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_SCAN_INTERVAL: 30}
    assert config_entry.runtime_data.update_interval.total_seconds() == 30
