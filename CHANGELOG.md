# Changelog

All notable changes to this integration are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.1] - 2026-10-14

🌟 **Highlights:** everything the integration shows is now in English and
German – including error messages and attribute names.

### ✨ Added

- 🏷️ The `int16` and `bits` attributes of the raw sensors have translated
  names (*Signed value (int16)* / *Wert mit Vorzeichen (int16)*,
  *Bit pattern* / *Bitmuster*).

### 🐛 Fixed

- 🌐 When the box cannot be reached or answers without data, Home Assistant
  now shows a translated message instead of the raw technical error. The
  details are still written to the debug log.

### 📚 Documentation

- 🔍 Data 13 is now described as the box's likely own surplus calculation;
  *Pgrid Bias* and the export limit are ruled out as the cause of its
  −2100 W limit.
- 🗣️ Hints from forums and the SolaX knowledge base added to the spec
  (hysteresis, common COM terminal, analog output, grid data source).

## [0.2.0] - 2026-10-12

🌟 **Highlights:** a tidier device page – every value appears only once –
and a new logo that shows what the box does: the sun feeds the adapter box,
which drives your water heater.

### ⚠️ Please check after updating

- 🧹 The raw sensors **Data 00–Data 09, Data 12, Data 13 and Data 14** are
  removed automatically – their values are shown by *Device time*,
  *Relay DO1–DO4*, *Grid power*, *Data 13 power* and *Battery*. If an
  automation, script or dashboard uses one of the removed sensors (e.g.
  `sensor.adapter_box_g2_data_14`), switch it to the matching new entity.
  The history of the removed sensors is no longer shown.

### ✨ Added

- 🎨 **New logo and icon**: the sun feeds the adapter box, which drives a
  water heater – light and dark variants, shown by Home Assistant 2026.3+
  under *Settings → Devices & services*.

### 🔄 Changed

- 🗂️ Raw `Data xx` sensors exist only for values that are not decoded yet
  (`Data 10`, `Data 11`, `Data 15`–`Data 17`), so every value appears only
  once on the device page.

### 📚 Documentation

- ⚖️ README starts with a disclaimer (independent and unofficial, not
  affiliated with SolaX) and ends with *Third-party documentation* and
  *Trademarks* sections; the new logo is shown as banner.

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
