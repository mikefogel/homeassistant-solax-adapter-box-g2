"""Tests for the read-only HTTP client (spec.md 3, 8)."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.solax_adapter_box_g2.api import (
    CannotConnect,
    InvalidResponse,
    SolaxAdapterBoxClient,
    normalize_host,
    serial_number,
)

from .conftest import HOST, SERIAL

URL = f"http://{HOST}/"


def _client(hass: HomeAssistant) -> SolaxAdapterBoxClient:
    return SolaxAdapterBoxClient(async_get_clientsession(hass), HOST, SERIAL)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("192.168.1.50", "192.168.1.50"),
        (" http://192.168.1.50/ ", "192.168.1.50"),
        ("HTTP://box.local", "box.local"),
    ],
)
def test_normalize_host(raw: str, expected: str) -> None:
    """A scheme and a trailing slash are removed (spec.md 4a)."""
    assert normalize_host(raw) == expected


def test_serial_number_accepts_both_spellings() -> None:
    """`sn` and `SN` are both accepted (spec.md 3b)."""
    assert serial_number({"sn": "SD1"}) == "SD1"
    assert serial_number({"SN": "SD2"}) == "SD2"
    assert serial_number({}) is None


async def test_read_realtime_posts_form_body(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, realtime: dict[str, Any]
) -> None:
    """The request is a form-encoded POST like `curl -d` (spec.md 3a)."""
    aioclient_mock.post(URL, text=json.dumps(realtime))

    assert await _client(hass).async_read_realtime() == realtime
    assert aioclient_mock.call_count == 1
    _, _, data, _ = aioclient_mock.mock_calls[0]
    assert data == {"optType": "ReadRealTimeData", "pwd": SERIAL}


async def test_read_settings_uses_read_set_data(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Settings are read with ReadSetData (spec.md 3e)."""
    aioclient_mock.post(URL, text='{"Data": [1, 2]}')

    assert await _client(hass).async_read_settings() == {"Data": [1, 2]}
    _, _, data, _ = aioclient_mock.mock_calls[0]
    assert data == {"optType": "ReadSetData", "pwd": SERIAL}


@pytest.mark.parametrize(
    "text", ["", "y", "Request method for this URI is not handled by server", "[1, 2]", '{"sn": "x"}']
)
async def test_unexpected_answer_is_invalid_response(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, text: str
) -> None:
    """Non-JSON, non-objects and answers without Data are rejected."""
    aioclient_mock.post(URL, text=text)

    with pytest.raises(InvalidResponse):
        await _client(hass).async_read_realtime()


@pytest.mark.parametrize("exc", [TimeoutError, aiohttp.ClientError])
async def test_connection_problems_are_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, exc: type[Exception]
) -> None:
    """Timeouts and client errors become CannotConnect."""
    aioclient_mock.post(URL, exc=exc)

    with pytest.raises(CannotConnect):
        await _client(hass).async_read_realtime()


async def test_http_error_is_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An HTTP error status becomes CannotConnect."""
    aioclient_mock.post(URL, status=500)

    with pytest.raises(CannotConnect):
        await _client(hass).async_read_realtime()


async def test_debug_log_does_not_contain_password(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    realtime: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The serial number in the answer is the password (spec.md 8)."""
    aioclient_mock.post(URL, text=json.dumps(realtime))
    caplog.set_level(logging.DEBUG, logger="custom_components.solax_adapter_box_g2")

    await _client(hass).async_read_realtime()

    assert "ReadRealTimeData answer" in caplog.text
    assert SERIAL not in caplog.text
