"""Constants for the SolaX Adapter Box G2 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "solax_adapter_box_g2"

MANUFACTURER: Final = "SolaX Power"
MODEL: Final = "Adapter Box G2"

CONF_SCAN_INTERVAL: Final = "scan_interval"

# Polling interval in seconds (spec.md 4b).
DEFAULT_SCAN_INTERVAL: Final = 10
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 300

# Timeout of one HTTP request in seconds (spec.md 5).
REQUEST_TIMEOUT: Final = 10

# Operations of the local API (spec.md 3e). Read operations only.
OPT_READ_REALTIME: Final = "ReadRealTimeData"
OPT_READ_SETTINGS: Final = "ReadSetData"

# ReadSetData is polled in every n-th cycle (spec.md 3e).
SETTINGS_POLL_EVERY: Final = 6

# Raw value arrays (spec.md 6a): source key -> unique ID suffix prefix.
SOURCE_DATA: Final = "data"
SOURCE_INFO: Final = "info"
SOURCE_SET: Final = "set"

# Data[0..5] is the device clock (spec.md 3c).
CLOCK_INDICES: Final = range(6)

# Decoded positions in Data (spec.md 3d).
RELAY_INDICES: Final = (6, 7, 8, 9)  # DO1-DO4
GRID_POWER_INDEX: Final = 12
DATA13_INDEX: Final = 13
BATTERY_SOC_INDEX: Final = 14

# Data positions shown by decoded entities only, without raw sensor (spec.md 6a).
DECODED_DATA_INDICES: Final = frozenset(
    (*CLOCK_INDICES, *RELAY_INDICES, GRID_POWER_INDEX, DATA13_INDEX, BATTERY_SOC_INDEX)
)

# Entries kept in the diagnostics change log (spec.md 7).
CHANGE_LOG_SIZE: Final = 500
