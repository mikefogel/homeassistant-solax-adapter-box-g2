# SolaX Adapter Box G2 – system specification

This document is binding for the integration: every behaviour described with
"must" is a requirement, and changes to the integration are specified here
before they are implemented. Section numbers are stable references used by
code comments, tests, and commit messages ("spec.md 5b"); a section that is
dropped keeps its number unused instead of being reassigned.

## 1. Purpose

A Home Assistant custom integration for the **SolaX Adapter Box G2**. The box
sits between a SolaX inverter (RS485) and up to four loads – heat pumps or
water heaters – and switches them through four dry contacts (DO1–DO4) or a
0–10 V analog output, depending on PV surplus, battery SOC and schedules
configured in SolaXCloud.

The local data format of the box is **not documented** by SolaX. The first
goal of this integration is therefore to **record every value the box
reports**, so that the meaning of each value can be found later by comparing
its history with what SolaXCloud shows (§7). Values are given a decoded
meaning (§3d) only once that meaning is confirmed on real hardware (one
exception on the user's request: `Data[13]`, §3d).

## 2. Core objectives

- Talk to the box locally over its HTTP API (§3), without the cloud.
- Configure everything through the Home Assistant UI (§4).
- Record **every** value of every response – undecoded values as raw
  sensors (§6a), decoded values as entities with unit and meaning (§6b) –
  so Home Assistant's recorder keeps a complete, comparable history.
- Decode values only where the meaning is certain (§3d, §6b); list
  everything else as an open hypothesis (§3c, §11).
- **Read only.** The integration must never send a command that changes the
  box's state or settings (§3e).
- Recover from connection loss on its own and show problems in the user's
  language, never as raw errors (§5, §8).

## 3. Device and protocol

### 3a. Request

The box is reached at `http://<host>/` with an HTTP `POST` whose
form-encoded body is

```text
optType=<operation>&pwd=<password>
```

- `<password>` is the box's **registration number**, which is the same as its
  serial number (SolaXCloud → device → *Registrierungsnummer*, e.g.
  `SDXXXXXXXX`). Serial numbers of Adapter Boxes start with `SD`.
- This is the same protocol as SolaX's Pocket WiFi dongles and SolaX EV
  chargers (sources: `nazar-pc/solax-local-api-docs`,
  `PatrikTrestik/homeassistant-solax-http`).

Confirmed on hardware (firmware `008.00`):

```text
curl -d "optType=ReadRealTimeData&pwd=SDXXXXXXXX" http://192.168.1.50
```

### 3b. Response of `ReadRealTimeData`

A JSON object. Observed on 2026-10-11 (firmware `008.00`):

```json
{"sn":"SDXXXXXXXX","ver":"008.00","type":0,"devKind":8,
 "Data":[9,42,22,11,10,26,0,0,0,0,0,1,0,409,75,1,0,1], ...}
```

The response continues after `Data` with an `Information` array of 10
mixed values (confirmed 2026-10-12 via diagnostics):
`[0.0, 0, "", 1, 1.0, 1.0, 1.0, 0.0, 0.0, 1]` – unchanged over the observed
hour, meaning unknown. The integration must accept any further top-level
fields, and must record `Information` the same way as `Data` when it is a
list (§6a).

| Field     | Observed   | Meaning                                                     |
|-----------|------------|-------------------------------------------------------------|
| `sn`      | SD…        | serial number = password; unique ID of the box (some SolaX devices send `SN`) |
| `ver`     | 008.00     | firmware version (matches SolaXCloud)                       |
| `type`    | 0          | unknown                                                     |
| `devKind` | 8          | device kind; probably "Adapter Box" (to be confirmed)       |
| `Data`    | 18 numbers | real-time values, see §3c                                   |

### 3c. `Data` array – known values and hypotheses

Status per index (**confirmed** = verified on hardware, **hypothesis** = to
be checked with the procedure of §7, **unknown** = no idea yet):

| Index | Observed | Status     | Meaning                                                     |
|-------|----------|------------|-------------------------------------------------------------|
| 0     | 9        | confirmed  | device clock: hour                                          |
| 1     | 42       | confirmed  | device clock: minute                                        |
| 2     | 22       | confirmed  | device clock: second                                        |
| 3     | 11       | confirmed  | device clock: day                                           |
| 4     | 10       | confirmed  | device clock: month                                         |
| 5     | 26       | confirmed  | device clock: year − 2000                                   |
| 6     | 0        | confirmed  | relay (dry contact) DO1: 0 = open, 1 = closed               |
| 7     | 0        | confirmed  | relay (dry contact) DO2: 0 = open, 1 = closed               |
| 8     | 0        | confirmed  | relay (dry contact) DO3: 0 = open, 1 = closed               |
| 9     | 0        | confirmed  | relay (dry contact) DO4: 0 = open, 1 = closed               |
| 10    | 0        | hypothesis | analog output voltage (the app showed 0 V), possibly scaled ÷10 or ÷100 |
| 11    | 1        | unknown    | status value (0/1), e.g. the box status shown in the app    |
| 12    | 0        | confirmed  | grid power in W, signed: positive = export, negative = import |
| 13    | 409      | hypothesis | power in W, signed: = inverter AC power − *available PV power* of the SolaX EV charger (strong correlation, see below); not the battery power |
| 14    | 75       | confirmed  | battery SOC in %, received from the inverter (unscaled, 0–100) |
| 15–17 | 1, 0, 1  | unknown    | status values (0/1); not the mode and not the remote switch (see below); `Data[15]` and `Data[17]` sometimes drop to 0 together for one sample |

**Relays `Data[6..9]` – confirmed on 2026-10-12** on real hardware
(firmware `008.00`): the four relays of the box drive solid-state relays
(SSRs) that switch a heating rod in four stages. The power of the heating
rod, measured with a Shelly Pro 3EM, follows the relay values exactly:

| Stage | Relays closed      | `Data[6..9]` | Heating rod power (nominal) | Measured |
|-------|--------------------|--------------|-----------------------------|----------|
| 0     | none               | 0, 0, 0, 0   | off                         | 0 W      |
| 1     | DO1                | 1, 0, 0, 0   | 400 W                       | ≈ 420 W  |
| 2     | DO1, DO2           | 1, 1, 0, 0   | 1.5 kW                      | ≈ 1.6 kW |
| 3     | DO1, DO2, DO3      | 1, 1, 1, 0   | 3 kW                        | ≈ 3.25 kW |
| 4     | DO1, DO2, DO3, DO4 | 1, 1, 1, 1   | 4.5 kW                      | ≈ 4.75 kW |

When stepping down, the box opened DO4, DO3 and DO2 one after another,
about 10 seconds apart, and closed DO2 again 30 seconds later. The stage
powers are a property of this installation, not of the box; the box only
reports the relay states.

**Battery SOC `Data[14]` – confirmed on 2026-10-12:** over 20 hours
(night discharge from about 72 % to 41 %, charge to 99–100 % by noon)
`Data[14]` follows the inverter's *Battery Capacity* (SolaX inverter
integration in Home Assistant) step by step and shows the same value. The
box receives it from the inverter for its SOC thresholds.

**Grid power `Data[12]` – confirmed on 2026-10-12:** from 06:00 to 18:30
`Data[12]` follows the inverter's *Grid Export* (SolaX inverter integration
in Home Assistant) peak for peak, up to about 6.4 kW, in watts without
scaling. The inverter integration only shows export (never below 0);
`Data[12]` also has negative values down to about −2.3 kW. These are grid
import, caused by control delays when the PV surplus drops. So `Data[12]`
is the signed grid power: positive = export, negative = import. The box
sends negative values as negative JSON numbers (e.g. `-2300`), not as
unsigned 16-bit numbers; the `int16` attribute (§6a) is therefore not needed
for this value. The box uses this value for its feed-in and consumption
thresholds (SG Ready signal conditions).

**`Data[13]` – strong correlation found on 2026-10-12, meaning open.**
Compared by hand at more than 20 points of a full day (CSV export of the
Home Assistant history, 06:00–18:30 local time) with the SolaX inverter
integration and the SolaX EV charger integration:

- `Data[13]` ≈ *Inverter Power* − *Available PV Power*, almost always
  within 50 W. *Available PV Power* is register `0x18` (signed, W) of the
  SolaX EV charger: the PV surplus the SolaX energy management considers
  available. The box and the EV charger share the inverter's RS485 bus
  (the box has a split RS485 port for EV chargers), so both very likely
  get their values from the same source.
- While the battery charges or discharges, *Available PV Power* is about 0
  and `Data[13]` ≈ *Inverter Power* (e.g. 07:34 UTC: −481 vs −406 W while
  the battery charged with +4.3 kW).
- Once the battery is full, `Data[13]` ≈ *Inverter Power* − *Available PV
  Power* (e.g. 13:00 UTC: 3113 − 5158 = −2045, `Data[13]` = −2029).
- `Data[13]` never went below about −2100 W during the day, even when
  *Available PV Power* was 6.2 kW – a limit whose origin is unknown.
- Rejected: `Data[13]` is **not** the battery power with inverted sign
  (14:00–16:00: battery ≈ 0 W while `Data[13]` was −2000 … +4000 W).

**Device clock – observed on 2026-10-12:** the box's clock runs exactly
**4 hours behind** local time (Europe/Berlin, CEST = UTC+2): diagnostics
downloaded at about 18:46:20 local time contained `Data[0..5]` =
14:46:18 on 12.10.26. Minutes and seconds match, so the clock is set to a
different time zone (UTC−2), not drifting. The *Device time* sensor (§6b)
shows the clock as reported; it is not corrected. Whether schedules set in
SolaXCloud are affected is unknown.

**Rarely changing values – history of 2026-10-12, 12:00–19:16 local time**
(CSV export and diagnostics change logs; PV rising and falling, heating rod
stepping between stages 0 and 4):

- `Data[10]` stayed 0 all day (the installation uses the relays, not the
  analog output).
- `Data[11]`, `Data[16]` stayed 1 and 0 all day; `Data[15]` and `Data[17]`
  stayed 1 except for the short drops in the table below.
- `Information[9]` (and the whole `Information` array) stayed unchanged. It
  was only *unavailable* together with all other sensors between 17:43 and
  17:55 local time, when the box did not answer for a few minutes (probably
  WLAN); the integration reconnected on its own each time (§5).

**Settings changes in SolaXCloud – test of 2026-10-12 evening** (relays all
open, diagnostics change logs 18:08–19:16:55 local time):

| Local time | Action in SolaXCloud          | Reaction in the local data            |
|------------|-------------------------------|---------------------------------------|
| 18:51:15   | none                          | `Data[15]` and `Data[17]` 0 for one sample |
| 19:06:45   | unknown (possibly mode → Manual) | `Data[15]` and `Data[17]` 0 for one sample |
| 19:14:01   | mode → Smart                  | none                                  |
| 19:16:02   | remote *Switch* → off         | none                                  |

Result: the mode (Smart/Manual) and the remote *Switch* are **not visible**
in the real-time data, neither as a lasting value nor as a short change;
the box reports measurements and relay states, not its configuration
(consistent with `ReadSetData` not being answered, §3e). `Data[15]` and
`Data[17]` always drop to 0 **together** for one sample; the cause is open.
Nobody operated the app at 18:51:15 and the relays were off. Hypothesis: a
status flag such as "communication with the inverter OK", where a single
missed RS485 poll shows as one 0.

What the box must know internally (from the user manual, chapter 5), and
where it was found:

| Internal value                                   | Found in the local data              |
|--------------------------------------------------|--------------------------------------|
| state of the dry contacts DO1–DO4                | `Data[6..9]`                         |
| grid power (feed-in / consumption)               | `Data[12]`                           |
| battery SOC from the inverter                    | `Data[14]`                           |
| analog output voltage (0–10 V), current gear (0–15) | not found yet (`Data[10]`?)       |
| mode (*Smart*/*Manual*), remote *Switch*         | not visible (test above)             |
| grid data source, per-load thresholds and times  | not visible; `ReadSetData` is not answered (§3e) |

Further findings from the research (sources in §3f):

- The SolaXCloud monitoring page of the box shows exactly three values:
  **status**, **analog output** and **current step of the dry contacts**.
  The dry contacts are `Data[6..9]` (confirmed); status and analog output
  are the most likely contents of `Data[10..17]`.
- In SG Ready mode the SolaX solution document says only DO1 switches by
  default; the user manual allows up to 4 loads on DO1–DO4. The observed
  installation has 4 loads of type *Water Heater* (load IDs `…01`–`…04`),
  which together form the four stages of one heating rod (table above).
- The box changes the step at most once about every 10 seconds; the default
  polling interval of 10 s (§4b) therefore sees every step.
- A schedule (up to 6 time windows) has the highest priority over all other
  conditions – this is what the correlation procedure of §7 uses.
- There is a "fallback step" for when communication with the inverter is
  lost.
- How SolaX encodes numbers elsewhere (EV charger, same local API):
  voltages and currents scaled ÷10 or ÷100, negative values as signed 16-bit
  numbers (attribute `int16`, §6a), 32-bit values as two consecutive
  positions (low word first, then high word). The Adapter Box itself sends
  negative values with a sign (`Data[12]`, `Data[13]`).
- The inverter's Modbus map only reports whether the Adapter Box is
  connected (input register `0xA1`, 0 = disconnected, 1 = connected); it has
  no dry contact states. The box's own local API (§3a) is therefore the
  only local source for them.
- The official SolaXCloud user API (V2) only returns inverter values; it
  documents no Adapter Box fields.
- Risk: on some SolaX WiFi modules a firmware update removed the local API.
  Firmware `008.00` of the box answers it.

### 3d. Decoded values

Only **confirmed** values are decoded (entities in §6b):

- `Data[0..5]` → device date and time.
- `Data[6..9]` → relay states DO1–DO4 and the number of closed relays.
- `Data[12]` → grid power in W (+ export, − import).
- `Data[14]` → battery SOC in %.

Exception on the user's request: `Data[13]` gets a power sensor in W
although its meaning is still open (§3c), so it can be used in dashboards
and statistics with the right unit.

A hypothesis becomes a decoded entity only after it is confirmed with §7 and
this table is updated.

### 3e. Operations used

| `optType`          | Purpose                      | Use                                   |
|--------------------|------------------------------|---------------------------------------|
| `ReadRealTimeData` | real-time values (§3b)       | every polling cycle                   |
| `ReadSetData`      | settings (read only)         | every 6th polling cycle, if supported |

`ReadSetData` is known from SolaX EV chargers. The Adapter Box G2 with
firmware `008.00` does **not** answer it with JSON (confirmed 2026-10-12:
`settings_supported: false` in the diagnostics). The request stays in the
integration for other firmware versions: if its first answer is not a JSON
object, the integration must log this once at INFO level and not send it
again until the integration is reloaded. A connection error does not count
as "not supported".

Write operations (e.g. `setReg`) must never be sent.

### 3f. Sources

- SolaX, *Adapter Box G2 User Manual* (chapters 2 and 5):
  <https://au.solaxpower.com/uploads/file/adapter-box-g2-user-manual-en.pdf>
- SolaX, *SolaX Heat Pump Solution – Adapter Box G2* V1.0:
  <https://www.sunfix.cz/wp-content/uploads/2024/04/ESS-Adapter-Box-Solution.pdf>
- SolaX, *Adapter Box G2 datasheet*:
  <https://solaxpower.com/uploads/file/solax-adpter-box-g2-datasheet-en.pdf>
- Local API of SolaX devices (request format, `SD` serials = Adapter Box,
  EV charger data map): <https://github.com/nazar-pc/solax-local-api-docs>
- SolaX EV charger integration (`ReadSetData`):
  <https://github.com/PatrikTrestik/homeassistant-solax-http>
- SolaX inverter Modbus integration (register `0xA1`):
  <https://github.com/wills106/homeassistant-solax-modbus>
- SolaXCloud User API V2:
  <https://global.solaxcloud.com/blue/4/user_api/2024/SolaXCloud_User_API_V2.pdf>
- Local API removed by a firmware update on other SolaX modules:
  <https://neilturner.me.uk/2024/10/26/so-long-solax-local-api/>

## 4. Configuration

### 4a. Setup (config flow)

The user enters:

- **Host** – IP address or host name of the box (a leading `http://` and a
  trailing `/` are removed).
- **Password** – the registration number (§3a).

The flow sends one `ReadRealTimeData` request. The entry is created only if
the answer is a JSON object with a `Data` list and a serial number (`sn` or
`SN`). The serial number becomes the entry's unique ID; setting up the same
box again aborts with "already configured" and updates the stored host
(new IP address after a router change). Errors are shown translated:

| Error              | Shown when                                          |
|--------------------|-----------------------------------------------------|
| `cannot_connect`   | no connection, timeout, or HTTP error               |
| `invalid_response` | an answer that is not the expected JSON (often a wrong password) |
| `unknown`          | any other unexpected error (logged with traceback)  |

### 4b. Options

- **Polling interval** in seconds: default 10, range 5–300. Changing it
  reloads the entry.

## 5. Polling and reconnection

- One update coordinator per box polls `ReadRealTimeData` at the polling
  interval; requests to one box are never sent in parallel.
- Each request has a timeout of 10 seconds.
- HTTP is stateless: there is no connection to keep open. **Reconnection**
  therefore means: when a request fails, all entities of the box become
  *unavailable*; polling continues at the normal interval, and the first
  successful answer makes them available again with fresh values. The loss
  is logged once with its reason and the recovery once at INFO level (no
  log entry per failed cycle; Home Assistant's update coordinator does
  this).
- If the box cannot be reached when Home Assistant starts, setup is retried
  automatically by Home Assistant (`ConfigEntryNotReady`).

## 6. Entities

All entities belong to one device per box: manufacturer *SolaX Power*,
model *Adapter Box G2*, firmware = `ver`, serial number = `sn`.

### 6a. Raw value sensors

For each index of each array the box reports, the integration creates one
sensor – **except for the `Data` positions that have a decoded entity**
(§6b): `Data[0..9]`, `Data[12]`, `Data[13]` and `Data[14]`. Their values are
shown by the decoded entities only; a raw sensor would show the same value
twice. With firmware `008.00` this leaves the raw sensors `Data 10`,
`Data 11`, `Data 15`–`Data 17` and `Information 00`–`Information 09`.

| Array                            | Entity name (en / de)              | Unique ID suffix |
|----------------------------------|------------------------------------|------------------|
| `Data` (`ReadRealTimeData`)      | Data 10 / Data 10                  | `data_10`        |
| `Information` (`ReadRealTimeData`) | Information 00 / Information 00  | `info_00`        |
| `Data` (`ReadSetData`)           | Setting 00 / Einstellung 00        | `set_00`         |

- The index is two-digit and equals the position in the JSON array, so a
  sensor can be matched to the raw response at a glance.
- The state is the value exactly as received. Numeric sensors get the state
  class *measurement*, so Home Assistant also keeps long-term statistics.
- Integer values 0–65535 have two extra attributes, recorded with the
  history: `int16` (the value as signed 16-bit number, for negative powers)
  and `bits` (16-digit binary, for status words that pack several flags).
- Raw sensors of decoded positions that exist from earlier versions
  (up to 0.1.0) are removed from Home Assistant's entity registry when the
  integration is set up, so no orphaned entities remain. Their recorded
  history is no longer shown; the decoded entities have their own history.
- When an array becomes longer later (e.g. after a firmware update), the new
  indices get sensors without a reload. When it becomes shorter, the
  missing indices become unavailable.
- Additionally, `type` and `devKind` are diagnostic sensors *Device type*
  and *Device kind*.

### 6b. Decoded sensors

- **Device time** (timestamp, diagnostic): `Data[0..5]` interpreted in Home
  Assistant's time zone; unknown when the values are not a valid date.

| Entity (en / de)                     | Platform      | Source       | Unit | Device class | State class |
|--------------------------------------|---------------|--------------|------|--------------|-------------|
| Relay DO1 … DO4 / Relais DO1 … DO4   | binary sensor | `Data[6..9]` | –    | –            | –           |
| Active relays / Aktive Relais        | sensor        | `Data[6..9]` | –    | –            | measurement |
| Grid power / Netzleistung            | sensor        | `Data[12]`   | W    | power        | measurement |
| Data 13 power / Data 13 Leistung     | sensor        | `Data[13]`   | W    | power        | measurement |
| Battery / Akku-Ladestand             | sensor        | `Data[14]`   | %    | battery      | measurement |

- **Relay DO*n***: *on* when the value is 1 (relay closed), *off* when it
  is 0.
- **Active relays**: the number of closed relays (0–4); with the observed
  installation this is the stage of the heating rod (§3c).
- **Grid power**: positive = export, negative = import, as the box reports
  it (note: Home Assistant's energy dashboard expects the opposite sign for
  a combined grid sensor).
- Decoded entities are created at setup and are *unavailable* while the
  answer has no numeric value at their position (e.g. a shorter `Data`
  array).

### 6c. Planned (after confirmation, §7)

- analog output voltage, gear, mode, switch – as far as found.

## 7. Correlation support

The user cannot watch the box all the time. Therefore:

- The recorder history of the raw and decoded sensors (§6) is the primary
  source. The
  README explains how to export it (*History → Download data*) together
  with notes on what happened at the same time in SolaXCloud.
- *Download diagnostics* must contain the last raw answers of both
  operations, whether `ReadSetData` is supported, and a **change log** of the
  last 500 value changes since the integration was loaded (time, value
  name, old value, new value). The clock values `Data[0..5]` are left out
  of the change log. The serial number and password are redacted.
- The README describes a procedure to confirm the hypotheses of §3c, e.g.
  forcing the loads on for a known time window in SolaXCloud
  (*Remote settings → Timing* or *Manual mode*) and checking which raw
  value changes at exactly that time.

## 8. Errors and logging

- Logging uses the logger of the integration's package
  (`custom_components.solax_adapter_box_g2`).
- The client raises clearly defined exceptions: `SolaxAdapterBoxError`
  (base), `CannotConnect`, `InvalidResponse`.
- Errors in the setup and options flow are shown with translated messages
  (§4a). Background polling never shows an error in the UI; it makes the
  entities unavailable (§5).
- Diagnostics and logs must never contain the password.

## 9. Packaging, tests, and release

- Domain `solax_adapter_box_g2`, `iot_class: local_polling`, no external
  Python requirements; translations in English and German with exactly the
  same keys.
- Set up through the UI only: YAML configuration is rejected
  (`CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)`).
- Brand icons inside the integration: `brand/icon.png` (256×256) and
  `brand/icon@2x.png` (512×512).
- The version in `manifest.json` equals the release tag without `v`.
- HACS repository (`hacs.json`); tests, tools, and developer files are
  excluded from release archives with `export-ignore` in `.gitattributes`.
- Tests with `pytest-homeassistant-custom-component`: pinned version in
  `requirements-test.txt` (Python 3.12) on every push, and the newest
  version weekly (Python 3.14). `hassfest` and HACS validation run in CI.
- Versions are tagged `vX.Y.Z`; a release is tagged only when CI is green
  for that commit. `CHANGELOG.md` uses the emoji headings of the project
  rules.

## 10. Acceptance criteria

- [ ] Setup with host and password creates one device with the box's serial
      number and firmware.
- [ ] Wrong host → "cannot connect"; non-JSON answer → "invalid response";
      same box twice → "already configured" with updated host.
- [ ] Every index of `Data`, `Information`, and `ReadSetData`'s `Data` has a
      sensor named after its index, except the decoded `Data` positions
      (§6a); raw sensors of decoded positions from earlier versions are
      removed from the entity registry.
- [ ] Integer raw sensors carry `int16` and `bits` attributes.
- [ ] *Device time* shows the box's clock.
- [ ] Relay DO1–DO4 follow `Data[6..9]`; *Active relays* counts the closed
      relays.
- [ ] *Grid power* (W, signed), *Data 13 power* (W, signed) and *Battery*
      (%) show `Data[12]`, `Data[13]` and `Data[14]` with unit and device
      class.
- [ ] Decoded entities are unavailable when their position is missing.
- [ ] A longer array adds sensors without a reload.
- [ ] When the box is unreachable, entities become unavailable and recover
      by themselves.
- [ ] `ReadSetData` that is not answered with JSON is not sent again.
- [ ] Diagnostics contain raw answers and the change log, without the
      serial number and password.
- [ ] No write operation is ever sent.

## 11. Open items

- Meaning of the `Information` array (§3b).
- Meaning of `Data[13]` (relation to the EV charger's *Available PV Power*,
  lower limit of about −2100 W).
- Meaning of `Data[10]`, `Data[11]`, `Data[15..17]`, including the cause of
  the joint short drops of `Data[15]` and `Data[17]`; then add decoded
  entities (§6c).
- Whether the device clock offset of 4 hours affects schedules set in
  SolaXCloud (§3c).
- Confirm that `devKind` 8 identifies the Adapter Box G2 (other SolaX
  devices would then be rejected or handled separately).
