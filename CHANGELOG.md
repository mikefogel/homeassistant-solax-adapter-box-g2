# Changelog

All notable changes to this integration are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-12

🌟 **Highlights:** the first decoded entities – relays, grid power and
battery with proper units, ready for dashboards and automations.

### ✨ Added

- 🔌 **Relay DO1–DO4** as binary sensors (on = relay closed).
- 🔢 **Active relays**: how many relays are closed (0–4) – with a staged
  heating rod this is the current stage.
- ⚡ **Grid power** in W (+ export, − import).
- 🔋 **Battery** SOC in %, as the box receives it from the inverter.
- 📈 **Data 13 power** in W, so `Data 13` can be charted with the right unit
  while its meaning is still being investigated.
- 🗂️ The raw `Data xx` sensors stay, so their history continues.

### 📚 Documentation

- ✅ **Confirmed:** `Data 06`–`Data 09` are the states of the relays
  DO1–DO4 (0 = open, 1 = closed), verified with SSRs switching a
  four-stage heating rod.
- ✅ **Confirmed:** `Data 14` is the battery SOC in % that the box receives
  from the inverter, verified against the inverter's *Battery Capacity*.
- ✅ **Confirmed:** `Data 12` is the grid power in W – positive = export,
  negative = import – verified against the inverter's *Grid Export*.
- 🔬 **Finding:** `Data 13` is a signed power in W that follows *inverter
  power − Available PV Power* of the SolaX wallbox within about 50 W over a
  whole day; it is not the battery power. Its exact meaning is still open.
- 🕰️ **Finding:** the box's clock runs 4 hours behind local time (CEST);
  *Device time* shows it as reported.
- ⚙️ **Finding:** firmware `008.00` does not answer `ReadSetData`, so there
  are no `Setting xx` sensors.
- 🔍 **Finding:** mode (Smart/Manual) and the remote switch set in
  SolaXCloud are not visible in the local data.
- 🔎 `spec.md` collects further research: what the SolaXCloud monitoring
  page shows (status, analog output, current step), how SolaX encodes
  numbers (÷10/÷100, signed 16-bit, 32-bit over two positions), and that
  the inverter only reports whether the box is connected. The value table
  has refined guesses for `Data 06`–`Data 17`, and a new source list.

## [0.0.1] - 2026-10-11

🌟 **Highlights:** the first version – it records every value of your
Adapter Box G2 so we can find out together what each one means.

### ✨ Added

- 🔌 Local, read-only connection to the SolaX Adapter Box G2 over its HTTP
  API, set up in the UI with IP address and registration number.
- 📊 One sensor per raw value (`Data 00`, `Data 01`, …) with long-term
  statistics and the extra attributes `int16` and `bits`.
- 🕒 *Device time* sensor showing the box's clock.
- ⚙️ `Setting xx` sensors, if the box answers `ReadSetData`.
- 🩺 *Download diagnostics* with the raw answers and a log of the last 500
  value changes – serial number and password are redacted.
- 🔁 Automatic recovery after connection loss.

### 📚 Documentation

- 🧭 README with a step-by-step guide to decode the values with SolaXCloud.
- 📐 `spec.md` with the protocol, the known values and the open hypotheses.
