# Changelog

All notable changes to this integration are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
