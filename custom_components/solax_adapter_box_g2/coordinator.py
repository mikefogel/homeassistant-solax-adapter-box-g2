"""Update coordinator: polling, reconnection and change log (spec.md 5, 7)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CannotConnect, InvalidResponse, SolaxAdapterBoxClient, SolaxAdapterBoxError
from .const import (
    CHANGE_LOG_SIZE,
    CLOCK_INDICES,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OPT_READ_SETTINGS,
    SETTINGS_POLL_EVERY,
    SOURCE_DATA,
    SOURCE_INFO,
    SOURCE_SET,
)

_LOGGER = logging.getLogger(__name__)

# Top-level fields that get their own sensor and appear in the change log.
TOP_LEVEL_FIELDS = ("type", "devKind", "ver")


@dataclass
class AdapterBoxData:
    """The last answers of the box."""

    realtime: dict[str, Any]
    settings: dict[str, Any] | None = None
    arrays: dict[str, list[Any]] = field(default_factory=dict)


def extract_arrays(
    realtime: dict[str, Any], settings: dict[str, Any] | None
) -> dict[str, list[Any]]:
    """Return the raw value arrays by source (spec.md 6a)."""
    arrays: dict[str, list[Any]] = {SOURCE_DATA: realtime["Data"]}
    if isinstance(realtime.get("Information"), list):
        arrays[SOURCE_INFO] = realtime["Information"]
    if settings is not None and isinstance(settings.get("Data"), list):
        arrays[SOURCE_SET] = settings["Data"]
    return arrays


class AdapterBoxCoordinator(DataUpdateCoordinator[AdapterBoxData]):
    """Poll one Adapter Box G2."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SolaxAdapterBoxClient,
    ) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        # None = not asked yet, False = not supported (spec.md 3e).
        self.settings_supported: bool | None = None
        self.change_log: deque[dict[str, Any]] = deque(maxlen=CHANGE_LOG_SIZE)
        self._cycle = 0

    async def _async_update_data(self) -> AdapterBoxData:
        """Read the box; a failure makes all entities unavailable (spec.md 5)."""
        try:
            realtime = await self.client.async_read_realtime()
        except SolaxAdapterBoxError as err:
            # The UI shows a translated message, the details go to the log (spec.md 8).
            _LOGGER.debug("Reading the box failed: %s", err)
            key = "invalid_response" if isinstance(err, InvalidResponse) else "cannot_connect"
            raise UpdateFailed(translation_domain=DOMAIN, translation_key=key) from err

        settings = self.data.settings if self.data else None
        if self.settings_supported is not False and self._cycle % SETTINGS_POLL_EVERY == 0:
            settings = await self._async_read_settings(settings)
        self._cycle += 1

        new = AdapterBoxData(
            realtime=realtime,
            settings=settings,
            arrays=extract_arrays(realtime, settings),
        )
        if self.data is not None:
            self._log_changes(self.data, new)
        return new

    async def _async_read_settings(
        self, previous: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Read ReadSetData; stop asking if the box does not support it."""
        try:
            settings = await self.client.async_read_settings()
        except InvalidResponse as err:
            if self.settings_supported is None:
                _LOGGER.info(
                    "The box does not answer %s (%s); not asking again until reload",
                    OPT_READ_SETTINGS,
                    err,
                )
                self.settings_supported = False
            return previous
        except CannotConnect as err:
            # A connection error says nothing about support (spec.md 3e).
            _LOGGER.debug("%s failed: %s", OPT_READ_SETTINGS, err)
            return previous
        self.settings_supported = True
        return settings

    def _log_changes(self, old: AdapterBoxData, new: AdapterBoxData) -> None:
        """Append every changed value to the change log (spec.md 7)."""
        now = dt_util.now().isoformat()
        for name in TOP_LEVEL_FIELDS:
            before, after = old.realtime.get(name), new.realtime.get(name)
            if before != after:
                self._append_change(now, name, before, after)
        for source in (SOURCE_DATA, SOURCE_INFO, SOURCE_SET):
            before_list = old.arrays.get(source, [])
            after_list = new.arrays.get(source, [])
            for index in range(max(len(before_list), len(after_list))):
                if source == SOURCE_DATA and index in CLOCK_INDICES:
                    continue
                before = before_list[index] if index < len(before_list) else None
                after = after_list[index] if index < len(after_list) else None
                if before != after:
                    self._append_change(now, f"{source}_{index:02d}", before, after)

    def _append_change(self, time: str, name: str, old: Any, new: Any) -> None:
        self.change_log.append({"time": time, "value": name, "old": old, "new": new})
