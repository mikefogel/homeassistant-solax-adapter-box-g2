"""Base entity of the SolaX Adapter Box G2 integration (spec.md 6)."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import AdapterBoxCoordinator


class AdapterBoxEntity(CoordinatorEntity[AdapterBoxCoordinator]):
    """An entity that belongs to the device of one box."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AdapterBoxCoordinator, key: str) -> None:
        """Initialize the entity; `key` is the unique ID suffix."""
        super().__init__(coordinator)
        serial = coordinator.config_entry.unique_id or coordinator.config_entry.entry_id
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=MODEL,
            serial_number=serial,
            sw_version=coordinator.data.realtime.get("ver") if coordinator.data else None,
        )
