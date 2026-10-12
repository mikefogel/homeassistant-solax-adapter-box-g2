<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/solax_adapter_box_g2/brand/dark_logo@2x.png">
    <img src="custom_components/solax_adapter_box_g2/brand/logo@2x.png" alt="Adapter Box G2 for Home Assistant" width="440">
  </picture>
</p>

# SolaX Adapter Box G2 for Home Assistant

[![Tests](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/tests.yml/badge.svg)](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/tests.yml)
[![Validate](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/validate.yml/badge.svg)](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/validate.yml)
[![Latest Home Assistant](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/latest-home-assistant.yml/badge.svg)](https://github.com/mikefogel/homeassistant-solax-adapter-box-g2/actions/workflows/latest-home-assistant.yml)

> **⚠️ Disclaimer — please read**
>
> This is an **independent, community-developed, unofficial** Home Assistant integration.
>
> - It is **not** created, endorsed, certified, sponsored, or supported by **SolaX Power Network Technology (Zhejiang) Co., Ltd.** ("SolaX") or any of its affiliates, and the author has no business relationship with SolaX.
> - "SolaX", "SolaXCloud", and "Adapter Box" are trademarks of SolaX, used in this repository only to identify the hardware this integration talks to (nominative use) — not to suggest any endorsement or partnership. The logo of this project is an original design and not a SolaX logo.
> - This integration was built from SolaX's own **publicly published** Adapter Box G2 documents (see "Documentation" below), public community documentation of the local API of other SolaX devices, and independent observation of real hardware. No confidential SolaX SDK, API, or internal documentation was used, and none is required to use or review this project.
> - **Use at your own risk.** This integration only reads from the box and never sends commands to it. Still, the author accepts no liability for damage to your installation, property, or data arising from its use.
> - Using third-party software with your installation may affect SolaX's own warranty or support terms — if in doubt, ask your installer or SolaX directly.
> - Provided **"as is", without warranty of any kind, express or implied** — see the MIT license at the bottom of this file for the exact legal terms.

A Home Assistant custom integration for the **SolaX Adapter Box G2**, the
box that switches heat pumps and water heaters through four dry contacts
(DO1–DO4) or a 0–10 V output, based on PV surplus.

> **Status: early, read-only.** SolaX does not document the box's local data
> format. This integration records **every value the box reports**: values
> whose meaning is confirmed get proper entities (relays, grid power,
> battery), the others are kept as raw sensors so their meaning can be found
> by comparing their history with SolaXCloud. The integration never changes
> anything on the box.

## Features

- Local polling over the box's HTTP API, no cloud needed.
- Setup in the UI with IP address and registration number.
- One sensor per not yet decoded raw value (`Data 10`, `Data 11`, …), named
  after its position in the box's answer, with long-term statistics.
- Extra attributes `int16` (signed value) and `bits` (16-digit binary) on
  every integer value, to spot negative powers and packed status flags.
- Decoded entities: *Relay DO1–DO4*, *Active relays*, *Grid power*,
  *Data 13 power* and *Battery*.
- *Device time* (the box's clock), *Device kind*, *Device type*.
- Settings sensors (`Setting 00`, …) if the box answers `ReadSetData`
  (firmware `008.00` does not).
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

**Decoded entities**

| Entity                | Meaning                                                    |
|-----------------------|------------------------------------------------------------|
| Relay DO1 – DO4       | on = relay closed (`Data 06`–`Data 09`)                    |
| Active relays         | number of closed relays, 0–4 (e.g. the stage of a heating rod) |
| Grid power            | W, + export / − import (`Data 12`) – note: the energy dashboard expects the opposite sign |
| Data 13 power         | W, signed (`Data 13`) – meaning still open, see below      |
| Battery               | battery SOC in % from the inverter (`Data 14`)             |

**Raw value entities** – only for positions that are not decoded yet;
`Data 00`–`Data 09`, `Data 12`, `Data 13` and `Data 14` are shown by the
decoded entities above.

| Entity              | Meaning                                                    |
|---------------------|------------------------------------------------------------|
| Data 10, Data 11    | not decoded yet – see [What we know](#what-we-know-so-far) |
| Data 15 – Data 17   | not decoded yet – see [What we know](#what-we-know-so-far) |
| Information xx      | only if the box sends an `Information` array               |
| Setting xx          | only if the box answers `ReadSetData` (not firmware 008.00) |
| Device time         | the box's clock (`Data 00`–`Data 05`)                      |
| Device kind / type  | `devKind` and `type` of the answer                         |

## What we know so far

Firmware `008.00`, see [spec.md §3c](spec.md) for details:

| Value     | Example | Meaning                                  |
|-----------|---------|------------------------------------------|
| Data 06–09 | 0      | ✅ relays DO1–DO4 (0 = open, 1 = closed) – confirmed with SSRs on a 4-stage heating rod |
| Data 10   | 0       | analog output voltage?                   |
| Data 12   | 0       | ✅ grid power in W: + export, − import – confirmed against the inverter's Grid Export |
| Data 13   | 409     | power in W ≈ inverter power − *Available PV Power* of the SolaX wallbox – plausibly the box's own surplus calculation (meaning not confirmed) |
| Data 14   | 75      | ✅ battery SOC in %, from the inverter – confirmed against the inverter's Battery Capacity |
| Data 11, 15–17 | 0/1 | status values (mode, switch, …)?       |

Good to know about the box itself: all four relays share **one COM
terminal**, and the box switches with a hysteresis and a minimum ON time per
load – so relays step down with a delay, not at a fixed threshold.

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

Regenerate the brand images after changing the design:

```bash
.venv/bin/python tools/brand_images.py
```

## Icon / branding

The integration ships its own brand images in
[`custom_components/solax_adapter_box_g2/brand/`](custom_components/solax_adapter_box_g2/brand/):
`icon.png` (256 px), `icon@2x.png` (512 px), `logo.png` and `logo@2x.png`,
each also as `dark_…` variant for dark themes. The motif is an original
design – the sun feeds the adapter box with its four contacts, which drives
a water heater – not the SolaX logo or any other vendor's. All images are
generated by [`tools/brand_images.py`](tools/brand_images.py).

Since Home Assistant 2026.3, custom integrations bring their brand images in
this `brand/` folder themselves
([announcement](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api)):
once the integration is installed or updated, Home Assistant shows them under
*Settings → Devices & services*. Older Home Assistant versions simply ignore
the folder.

## Documentation

- [System specification](spec.md) — binding description of every behaviour,
  including everything known about the box's data; changes are specified
  there first
- [Changelog](CHANGELOG.md)
- [SolaX Adapter Box G2 user manual](https://au.solaxpower.com/uploads/file/adapter-box-g2-user-manual-en.pdf)
  (hosted by SolaX, see "Third-party documentation" below)
- [SolaX Adapter Box G2 datasheet](https://solaxpower.com/uploads/file/solax-adpter-box-g2-datasheet-en.pdf)
  (hosted by SolaX)
- [Home Assistant documentation](https://www.home-assistant.io/)

## Third-party documentation

This repository's own MIT license (below) covers only the integration's code
and documentation. The SolaX Adapter Box G2 documents are © SolaX and are not
distributed with this repository — they are linked, hosted on SolaX's own
sites, under "Documentation" above.

## Trademarks

"SolaX", "SolaXCloud", and "Adapter Box" are trademarks of SolaX Power
Network Technology (Zhejiang) Co., Ltd. This project is an independent,
unofficial integration, not affiliated with, endorsed by, or sponsored by
SolaX; the names are used solely to identify the hardware this integration
is compatible with (nominative use).

## License

MIT. See [LICENSE](LICENSE). The license covers this repository's own code
and documentation only — see "Third-party documentation" and "Trademarks"
above for what it does not cover.
