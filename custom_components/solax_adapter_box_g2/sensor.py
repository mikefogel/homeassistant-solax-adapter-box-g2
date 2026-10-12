"""Sensors: one per raw value, plus decoded values (spec.md 6a, 6b)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import AdapterBoxConfigEntry
from .const import (
    BATTERY_SOC_INDEX,
    DATA13_INDEX,
    DECODED_DATA_INDICES,
    DOMAIN,
    GRID_POWER_INDEX,
    RELAY_INDICES,
    SOURCE_DATA,
)
from .coordinator import AdapterBoxCoordinator
from .entity import AdapterBoxEntity, data_number


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AdapterBoxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors; new array indices are added later (spec.md 6a)."""
    coordinator = entry.runtime_data
    known: set[tuple[str, int]] = set()
    _remove_old_raw_sensors(hass, entry)

    @callback
    def _add_new_raw_sensors() -> None:
        if coordinator.data is None:
            return
        new: list[SensorEntity] = []
        for source, values in coordinator.data.arrays.items():
            for index, value in enumerate(values):
                if source == SOURCE_DATA and index in DECODED_DATA_INDICES:
                    continue
                if (source, index) not in known:
                    known.add((source, index))
                    new.append(RawValueSensor(coordinator, source, index, value))
        if new:
            async_add_entities(new)

    async_add_entities(
        [
            DeviceTimeSensor(coordinator),
            TopLevelSensor(coordinator, "type", "device_type"),
            TopLevelSensor(coordinator, "devKind", "device_kind"),
            ActiveRelaysSensor(coordinator),
            DataValueSensor(
                coordinator,
                "grid_power",
                GRID_POWER_INDEX,
                UnitOfPower.WATT,
                SensorDeviceClass.POWER,
            ),
            DataValueSensor(
                coordinator,
                "data13_power",
                DATA13_INDEX,
                UnitOfPower.WATT,
                SensorDeviceClass.POWER,
            ),
            DataValueSensor(
                coordinator,
                "battery_soc",
                BATTERY_SOC_INDEX,
                PERCENTAGE,
                SensorDeviceClass.BATTERY,
            ),
        ]
    )
    _add_new_raw_sensors()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_raw_sensors))


@callback
def _remove_old_raw_sensors(hass: HomeAssistant, entry: AdapterBoxConfigEntry) -> None:
    """Remove raw sensors of decoded positions from earlier versions (spec.md 6a)."""
    registry = er.async_get(hass)
    serial = entry.unique_id or entry.entry_id
    for index in DECODED_DATA_INDICES:
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{serial}_{SOURCE_DATA}_{index:02d}"
        )
        if entity_id is not None:
            registry.async_remove(entity_id)


def raw_attributes(value: Any) -> dict[str, Any] | None:
    """Return `int16` and `bits` for integers 0-65535 (spec.md 6a)."""
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFF:
        return None
    return {
        "int16": value - 0x10000 if value > 0x7FFF else value,
        "bits": format(value, "016b"),
    }


class RawValueSensor(AdapterBoxEntity, SensorEntity):
    """One position of a raw value array, exactly as received."""

    def __init__(
        self,
        coordinator: AdapterBoxCoordinator,
        source: str,
        index: int,
        first_value: Any,
    ) -> None:
        """Initialize the sensor; the first value decides the state class."""
        super().__init__(coordinator, f"{source}_{index:02d}")
        self._source = source
        self._index = index
        self._attr_translation_key = f"raw_{source}"
        self._attr_translation_placeholders = {"index": f"{index:02d}"}
        if isinstance(first_value, (int, float)) and not isinstance(first_value, bool):
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def _value(self) -> Any:
        values = self.coordinator.data.arrays.get(self._source, [])
        return values[self._index] if self._index < len(values) else None

    @property
    def available(self) -> bool:
        """Unavailable when the array no longer has this index."""
        return super().available and self._value is not None

    @property
    def native_value(self) -> Any:
        """Return the raw value."""
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the signed and binary views of the value."""
        return raw_attributes(self._value)


class TopLevelSensor(AdapterBoxEntity, SensorEntity):
    """A top-level field of the real-time answer, e.g. `devKind`."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: AdapterBoxCoordinator, field: str, translation_key: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, translation_key)
        self._field = field
        self._attr_translation_key = translation_key

    @property
    def native_value(self) -> Any:
        """Return the field's value."""
        return self.coordinator.data.realtime.get(self._field)


class DataValueSensor(AdapterBoxEntity, SensorEntity):
    """A decoded Data position with unit and device class (spec.md 6b)."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: AdapterBoxCoordinator,
        key: str,
        index: int,
        unit: str,
        device_class: SensorDeviceClass,
    ) -> None:
        """Initialize the sensor; `key` is unique ID suffix and translation key."""
        super().__init__(coordinator, key)
        self._index = index
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def available(self) -> bool:
        """Unavailable while the answer has no number at this position."""
        return super().available and data_number(self.coordinator, self._index) is not None

    @property
    def native_value(self) -> int | float | None:
        """Return the value as reported by the box."""
        return data_number(self.coordinator, self._index)


class ActiveRelaysSensor(AdapterBoxEntity, SensorEntity):
    """Number of closed relays DO1-DO4 (spec.md 6b)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "active_relays"

    def __init__(self, coordinator: AdapterBoxCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "active_relays")

    def _relays(self) -> list[int | float | None]:
        return [data_number(self.coordinator, index) for index in RELAY_INDICES]

    @property
    def available(self) -> bool:
        """Unavailable while a relay position is missing."""
        return super().available and None not in self._relays()

    @property
    def native_value(self) -> int | None:
        """Return how many relays are closed."""
        relays = self._relays()
        if None in relays:
            return None
        return sum(1 for value in relays if value == 1)


def device_time(data: list[Any]) -> datetime | None:
    """Decode Data[0..5] = hour, minute, second, day, month, year-2000."""
    try:
        hour, minute, second, day, month, year = (int(v) for v in data[:6])
        return datetime(
            2000 + year,
            month,
            day,
            hour,
            minute,
            second,
            tzinfo=dt_util.get_default_time_zone(),
        )
    except (TypeError, ValueError):
        return None


class DeviceTimeSensor(AdapterBoxEntity, SensorEntity):
    """The clock of the box (spec.md 6b)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "device_time"

    def __init__(self, coordinator: AdapterBoxCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "device_time")

    @property
    def native_value(self) -> datetime | None:
        """Return the decoded device time."""
        return device_time(self.coordinator.data.arrays.get(SOURCE_DATA, []))
