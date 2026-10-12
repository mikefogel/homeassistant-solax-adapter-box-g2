"""Binary sensors: relay states DO1-DO4 (spec.md 6b)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AdapterBoxConfigEntry
from .const import RELAY_INDICES
from .coordinator import AdapterBoxCoordinator
from .entity import AdapterBoxEntity, data_number


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdapterBoxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one binary sensor per relay."""
    coordinator = entry.runtime_data
    async_add_entities(
        RelaySensor(coordinator, number, index)
        for number, index in enumerate(RELAY_INDICES, start=1)
    )


class RelaySensor(AdapterBoxEntity, BinarySensorEntity):
    """A relay (dry contact) of the box: on = closed."""

    _attr_translation_key = "relay"

    def __init__(self, coordinator: AdapterBoxCoordinator, number: int, index: int) -> None:
        """Initialize the relay sensor."""
        super().__init__(coordinator, f"relay_do{number}")
        self._index = index
        self._attr_translation_placeholders = {"number": str(number)}

    @property
    def available(self) -> bool:
        """Unavailable while the answer has no number at this position."""
        return super().available and data_number(self.coordinator, self._index) is not None

    @property
    def is_on(self) -> bool | None:
        """Return True when the relay is closed."""
        value = data_number(self.coordinator, self._index)
        return None if value is None else value == 1
