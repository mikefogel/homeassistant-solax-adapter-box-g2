"""Shared fixtures and two environment workarounds.

1. Importing `custom_components` here, before any fixture runs, makes this
   repository's package win the `sys.modules["custom_components"]` race
   against the same-named test package shipped with
   pytest-homeassistant-custom-component.

2. pycares (the DNS resolver behind Home Assistant's aiohttp session) starts
   one process-wide daemon thread when its first channel is created. The
   harness would report it as a thread left behind by whichever test happens
   to create the first session, so it is started here, before any test.
"""

from __future__ import annotations

from collections.abc import Generator
import copy
from typing import Any
from unittest.mock import AsyncMock, patch

import custom_components
import pytest

from homeassistant.const import CONF_HOST, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solax_adapter_box_g2.const import DOMAIN

assert custom_components  # imported only to win the sys.modules race, see (1)

try:  # see (2); private API, therefore optional
    import pycares

    pycares._shutdown_manager.start()  # noqa: SLF001
except (ImportError, AttributeError):
    pass

SERIAL = "SDXXXXXXXX"
HOST = "192.168.1.50"

# Answer observed on real hardware on 2026-10-11 (spec.md 3b).
REALTIME: dict[str, Any] = {
    "sn": SERIAL,
    "ver": "008.00",
    "type": 0,
    "devKind": 8,
    "Data": [9, 42, 22, 11, 10, 26, 0, 0, 0, 0, 0, 1, 0, 409, 75, 1, 0, 1],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading the integration from custom_components."""


@pytest.fixture
def realtime() -> dict[str, Any]:
    """Return a fresh copy of the observed real-time answer."""
    return copy.deepcopy(REALTIME)


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for the observed box."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Adapter Box G2",
        unique_id=SERIAL,
        data={CONF_HOST: HOST, CONF_PASSWORD: SERIAL},
    )


@pytest.fixture
def mock_client(realtime: dict[str, Any]) -> Generator[AsyncMock]:
    """Patch the client's read methods; ReadSetData is unsupported by default."""
    from custom_components.solax_adapter_box_g2.api import InvalidResponse

    with (
        patch(
            "custom_components.solax_adapter_box_g2.api.SolaxAdapterBoxClient.async_read_realtime",
            new_callable=AsyncMock,
            return_value=realtime,
        ) as read_realtime,
        patch(
            "custom_components.solax_adapter_box_g2.api.SolaxAdapterBoxClient.async_read_settings",
            new_callable=AsyncMock,
            side_effect=InvalidResponse("not JSON"),
        ) as read_settings,
    ):
        client = AsyncMock()
        client.read_realtime = read_realtime
        client.read_settings = read_settings
        yield client
