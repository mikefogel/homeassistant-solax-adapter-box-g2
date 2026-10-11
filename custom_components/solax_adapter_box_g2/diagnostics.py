"""Downloadable diagnostics for correlating raw values (spec.md 7)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from . import AdapterBoxConfigEntry

# The serial number is the password (spec.md 3a), so it is redacted too.
TO_REDACT = {CONF_PASSWORD, "sn", "SN", "unique_id", "serial_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AdapterBoxConfigEntry
) -> dict[str, Any]:
    """Return raw answers, settings support and the change log."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "settings_supported": coordinator.settings_supported,
        "realtime": async_redact_data(data.realtime, TO_REDACT) if data else None,
        "settings": (
            async_redact_data(data.settings, TO_REDACT)
            if data and data.settings is not None
            else None
        ),
        "change_log": list(coordinator.change_log),
    }
