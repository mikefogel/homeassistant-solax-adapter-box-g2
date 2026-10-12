"""The SolaX Adapter Box G2 integration (see spec.md)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SolaxAdapterBoxClient
from .const import DOMAIN
from .coordinator import AdapterBoxCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

# Set up through the UI only (spec.md 4).
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type AdapterBoxConfigEntry = ConfigEntry[AdapterBoxCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AdapterBoxConfigEntry) -> bool:
    """Set up one box; an unreachable box makes Home Assistant retry (spec.md 5)."""
    client = SolaxAdapterBoxClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PASSWORD],
    )
    coordinator = AdapterBoxCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AdapterBoxConfigEntry) -> bool:
    """Unload one box."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: AdapterBoxConfigEntry) -> None:
    """Reload after the options changed (spec.md 4b)."""
    await hass.config_entries.async_reload(entry.entry_id)
