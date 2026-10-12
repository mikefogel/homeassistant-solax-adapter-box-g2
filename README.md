# SolaX Adapter Box G2 for Home Assistant

[![Tests](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/tests.yml/badge.svg)](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/tests.yml)
[![Validate](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/validate.yml/badge.svg)](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/validate.yml)
[![Latest Home Assistant](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/latest-home-assistant.yml/badge.svg)](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/latest-home-assistant.yml)

A Home Assistant custom integration for the **SolaX Adapter Box G2**, the
box that switches heat pumps and water heaters through four dry contacts
(DO1–DO4) or a 0–10 V output, based on PV surplus.

> **Status: early, read-only.** SolaX does not document the box's local data
> format. This version therefore records **every value the box reports** as
> its own sensor, so the meaning of each value can be found by comparing its
> history with SolaXCloud. Decoded entities (e.g. one binary sensor per dry
> contact) follow once a value is confirmed. The integration never changes
> anything on the box.

## Features

- Local polling over the box's HTTP API, no cloud needed.
- Setup in the UI with IP address and registration number.
- One sensor per raw value (`Data 00`, `Data 01`, …), named after its
  position in the box's answer, with long-term statistics.
- Extra attributes `int16` (signed value) and `bits` (16-digit binary) on
  every integer value, to spot negative powers and packed status flags.
- *Device time* (the box's clock), *Device kind*, *Device type*.
- Settings sensors (`Setting 00`, …) if the box answers `ReadSetData`.
- *Download diagnostics* with the raw answers and a log of the last 500
  value changes.
- Automatic recovery after connection loss.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → *Custom repositories*.
2. Repository `https://github.com/mikefogel/homeassistant-solax-adapter-box-g2`,
   type *Integration*.
3. Install **SolaX Adapter Box G2** and restart Home Assistant.

### Manually

Copy `custom_components/solax_adapter_box_g2` into the `custom_components`
folder of your Home Assistant configuration and restart Home Assistant.

## Setup

*Settings → Devices & services → Add integration → SolaX Adapter Box G2.*

| Field               | Value                                                                 |
|---------------------|-----------------------------------------------------------------------|
| Host                | IP address of the box, e.g. `192.168.1.50` (give it a fixed IP in your router) |
| Registration number | SolaXCloud → Adapter Box G2 → *Registrierungsnummer*, e.g. `SDXXXXXXXX` (same as the serial number) |

The polling interval (default 10 s, 5–300 s) can be changed under
*Configure*.

You can test the connection from the Home Assistant terminal first:

```bash
curl -d "optType=ReadRealTimeData&pwd=<registration number>" http://<IP address>
```

## Entities

| Entity              | Meaning                                                    |
|---------------------|------------------------------------------------------------|
| Data 00 – Data 05   | the box's clock (hour, minute, second, day, month, year); disabled by default |
| Data 06 – Data 09   | relays DO1–DO4: 0 = open, 1 = closed (confirmed)           |
| Data 10 – Data 11   | not decoded yet – see [What we know](#what-we-know-so-far) |
| Data 12             | grid power in W: + export, − import (confirmed)            |
| Data 13             | not decoded yet – see [What we know](#what-we-know-so-far) |
| Data 14             | battery SOC in %, from the inverter (confirmed)            |
| Data 15 – Data 17   | not decoded yet – see [What we know](#what-we-know-so-far) |
| Information xx      | only if the box sends an `Information` array               |
| Setting xx          | only if the box answers `ReadSetData`                      |
| Device time         | `Data 00`–`Data 05` combined                               |
| Device kind / type  | `devKind` and `type` of the answer                         |

## What we know so far

Firmware `008.00`, see [spec.md §3c](spec.md) for details:

| Value     | Example | Meaning                                  |
|-----------|---------|------------------------------------------|
| Data 06–09 | 0      | ✅ relays DO1–DO4 (0 = open, 1 = closed) – confirmed with SSRs on a 4-stage heating rod |
| Data 10   | 0       | analog output voltage?                   |
| Data 12   | 0       | ✅ grid power in W: + export, − import – confirmed against the inverter's Grid Export |
| Data 13   | 409     | power in W ≈ inverter power − *Available PV Power* of the SolaX wallbox (strong correlation, meaning open) |
| Data 14   | 75      | ✅ battery SOC in %, from the inverter – confirmed against the inverter's Battery Capacity |
| Data 11, 15–17 | 0/1 | status values (mode, switch, …)?       |

## Help decode the values

You don't need to watch the box – Home Assistant records everything. Just
make sure something *happens* at a time you know:

1. **Let the integration run** for at least a day, ideally a sunny one.
2. **Cause a known event** and write down the time, e.g.:
   - SolaXCloud → Adapter Box → *Funktionssteuerung → Remoteeinstellungen →
     Timing*: a 15-minute window, e.g. 12:00–12:15, in which the loads must
     run, or
   - switch *Modus* between *Smart* and *Manual*, or the remote *Switch*
     off and on again, or
   - look at *Funktionssteuerung → Betriebszustand* when a dry contact is
     green, and note the time and which contact.
3. **Check the history:** *History* → add the entities `Data 10`, `Data 11`, `Data 13` and `Data 15` … `Data 17`
   → look for a value that changes at exactly that time.
4. **Share the result:** download the history as CSV (*History* → ⋮ →
   *Download data*) and the diagnostics (device page → ⋮ → *Download
   diagnostics*), and add your notes. The diagnostics contain no serial
   number or password.

## Troubleshooting

- **"The box cannot be reached"** – check the IP address and that the box
  is online in SolaXCloud. Home Assistant and the box must be in the same
  network.
- **"The box answered, but not with data"** – usually a wrong registration
  number.
- **Entities unavailable** – the box did not answer. The integration keeps
  polling and recovers by itself.
- **Debug log** – add to `configuration.yaml`:

  ```yaml
  logger:
    logs:
      custom_components.solax_adapter_box_g2: debug
  ```

  The serial number / password is masked in the log.

## Development

The binding specification is [spec.md](spec.md).

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
```

## License

[MIT](LICENSE)
