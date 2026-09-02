# Hardware readiness — Milestone 5

Current safety level: **Simulation**. This is a documentation/evidence audit, not a
hardware test. No real adapter, adapter skeleton, connection, device discovery, register
read/write or deployment exists as a result of Milestone 5. Real enable, homing and motion
remain prohibited. Readiness is assessed from the [evidence matrix](evidence-matrix.md),
not from assuming that historical code still describes the rig.

## Gate decisions

| Gate | Current result | Evidence / outstanding decision |
|---|---|---|
| A — Offline codec readiness | **PASS** | Committed Milestone 4 (`0031e4b`); pure codecs, conservative catalog, fake transport, allowlists, ambiguity preservation and offline tests. Entry checks: Ruff and format pass, mypy 32 source files, pytest 164 passed. Only synthetic behavior is demonstrated. |
| B — Real raw read readiness | **BLOCKED** | Exact target/firmware and compatible communication manual absent; adapter/wiring/settings and read FC/address convention unresolved; no approved safe energization, disabled-state/restraint or first-read procedure. |
| C — Trusted typed telemetry readiness | **BLOCKED** | B plus speed width, wire representation, active 32-bit layout, independent observations, plausibility/freshness and repeatability remain unverified. |
| D — Motion readiness | **BLOCKED** | Independent safety, PL/NL, HSW, homing, joint calibration, direction, travel limits, holding/brake behavior and qualified review unresolved. |

Passing A grants **no hardware permission**. Passing B would authorize only its exact
bounded raw acquisition, not trusted physical interpretation. Passing C would not grant
motion permission. None of these decisions automatically changes configuration, state,
lease, homing or servo enablement.

### Gate A acceptance

Retain strict U16/I16/U32/I32 validation, signed/boundary/negative vectors and all four
explicit layouts; preserve raw words and documentary metadata. Symbolic allowlists remain
immutable; engineering reads remain disabled by default; displacement is not allowlisted.
Unknown area/address/layout and malformed responses fail closed. Speed ambiguity must
not become trusted telemetry. Fake checksums are injected failures, not real RTU CRC tests.
No source/test changes are needed for this audit.

### Gate B acceptance — before concrete adapter implementation or physical use

The following evidence package and design review are required **before implementation**.
Actual physical use additionally requires completion of offline adapter validation and
fresh, explicit authorization for the exact physical test. A document review cannot
authorize that test implicitly.

- Identify the exact drive, motor and firmware; assess compatibility of the complete
  manufacturer communication manual, including supported RTU framing and read behavior.
- Confirm the actual adapter model/revision, isolation/direction behavior, drive and
  adapter pinouts, A/B/reference wiring, biasing, termination, power and USB topology.
- Confirm actual station, baud, data bits, parity, stop bits and response delay. Select a
  bounded host timeout justified by the matched documentation; legacy defaults are not
  measurements. No broadcast, station discovery or settings scan.
- Confirm the harmless read function code for the chosen area. A manufacturer-supported
  safe discovery procedure could be reviewed separately, but none is supplied or approved
  now; guessing 03/04 is not a substitute.
- Confirm transport address convention, or review a bounded evidence-derived candidate
  plan with at most two candidates and separate approval before each. No range scan,
  arithmetic fallback, write-only register or trigger probing.
- Confirm response length, byte-to-word assembly, exception and CRC checks, request-size
  constraints and timing. Raw bytes may be retained without claiming physical units.
- Approve a qualified safe-energization and mechanical-restraint plan, including gravity
  and brake behavior. The servo must be independently confirmed disabled, with no motion
  command path and no dependence on software alone to prevent a hazard.
- Define a fixed symbolic read allowlist, sole Pi-side serial owner and least-privilege
  device access. The first test permits one reviewed U16 request, one outstanding request,
  one bounded timeout and zero retries; end after success or first error. No GUI connection,
  monitoring service, background polling or automatic recovery is part of that test.
- Record operator/reviewer, exact test authorization, stop conditions and full capture
  template before access. Hardware-facing phases in the [commissioning design](read-only-commissioning.md)
  remain future work, separately authorized.

Unknown 32-bit layout does **not** by itself block an otherwise approved one-word raw
read. Unresolved speed width blocks selecting that field/count, not every U16 field.
Joint-angle calibration and HSW commissioning belong to D, not raw acquisition. However,
unknown load restraint or safe disabled-state energization still blocks B. Scope the
evidence requirements to the selected test; never use these distinctions to waive safety.

### Gate C acceptance — per field, not a global telemetry approval

Require the matched width, signedness and wire representation, unit and exact scale.
For 32-bit fields require independently validated byte/word order and coherent two-word
acquisition, with evidence of any shared layout rule before reuse across registers.
Compare against a keypad or other independent physical observation, with recorded
plausibility bounds and bounded repeated reads. Preserve acquisition time, monotonic age,
sequence, raw words, source, validity and stale/error indication; missing data is not zero.
Resolve speed width before reporting its scalar. Application units stay application units;
calibrated joint degrees are a separate D prerequisite. Neither telemetry nor a status
value proves electrical isolation, safe holding torque, an effective E-stop or motion readiness.

### Gate D acceptance — remains out of scope

Require approved independent E-stop and STO/enable/contactor protection as applicable to
the exact drive; installed PL/NL with verified wiring, levels, placement and stopping
distance; HSW and the selected drive-internal homing method; mechanical hard stops, safe
range and direction; validated joint conversion/zero/backlash assumptions; brake and
gravity/holding behavior; qualified electrical and mechanical review; and separately
approved bounded low-energy procedures. Controlled stop is not an emergency stop. Do not
automatically issue Servo Off when loss of holding torque has not been validated.
No unattended real-hardware endurance test is authorized. Fault reset, reconnect, startup,
GUI reconnect and lease recovery never automatically enable, home, move or resume.

## Prioritized user evidence request

Start with existing files and safely accessible exterior labels. These are information
requests, **not permission to power equipment, open an energized enclosure, touch live
wiring, connect a commissioning tool, change a parameter or test a brake**. If access needs
isolation or enclosure opening, stop and use a qualified person and approved isolation
procedure. Separately authorize any powered observation. Redact serial numbers, asset IDs,
hostnames and private network details; credentials, tokens and private keys are not needed.

| Priority | What / usual location | Why needed | Power / read-only / qualification / redaction |
|---|---|---|---|
| 1 | Drive and motor nameplate photos; existing purchase/model records; exact compatible full A6-RS communication manual and motor datasheet | Establish installed identities, firmware applicability, supply/brake/encoder specifications and protocol rules | No power needed for labels/files; read-only observation. Qualified person if labels are inside an enclosure or require isolation. Redact serials; retain model/rating text. |
| 2 | Adapter front/back/model labels; existing electrical schematic; control-terminal labels and RS485 A/B/reference cable photos | Confirm exact adapter, pinout, isolation, direction control, termination/bias and actual wiring, including custom RJ45 cable | Equipment isolated where access requires it; qualified electrical person only for enclosure/wiring inspection. Read-only, no rewiring. Redact asset IDs. |
| 3 | Existing drive version and communication-setting records; if absent, propose safely accessible external keypad observations of the exact manual's version and C0A Modbus setting labels | Confirm actual firmware, station/format/baud/response delay and C0A.06, not factory defaults or commissioning-software settings | Records need no power. New display observations need separate powered authorization and safe disabled/restraint review. Qualified operator; view only, no edit/confirmation actions or tool connection. Redact serials. |
| 4 | Existing assembly/gearbox/brake drawings, isolated overview photos and signed safety/energization review | Resolve gravity, brake supply/control and holding risk before a disabled raw read; distinguish later PL/NL/HSW/calibration evidence | Existing records or isolated photos; read-only. Qualified mechanical/electrical reviewer for conclusions. Do not release brake, move load or test switches now. |
| 5 | Existing Pi board/OS inventory and USB/power topology; later approved local OS/Python/architecture, by-id and permission observations | Define the intended host and unique owner without guessing a port or granting permissions | Existing records first. Any new Pi access is future-only and separately authorized; read-only qualified maintainer observation, no device/network scan now. Share sanitized output only, never credentials. |
| 6 | Any original raw request/response log plus its capture context and independently observed display value | May narrow FC/address/layout uncertainty without another hardware session | Existing file only; no capture generation requested. Retain bytes/CRC context and settings; redact unrelated identifiers/secrets. Missing metadata remains explicitly missing. |

Useful historical leads, not confirmed identities: D's bibliography names motor datasheet
`A6M80-750H2B1-M17_Full_Datasheet.pdf`; the adapter illustration says Waveshare USB TO
RS232/485/TTL; the worm-gear bibliography suggests NMRVS50/50:1. Confirm each from installed
labels; do not purchase, wire or configure from these leads.

## Smallest safe next milestone

Milestone 6 proposal: **offline evidence intake and Gate B reassessment only**. Review
user-supplied redacted labels, exact communication manual and existing wiring/settings
records; update evidence provenance and decide whether a first-read specification can be
reviewed. Do not add an adapter skeleton, code, device discovery or hardware access.
If evidence remains missing, keep B blocked. Even a future B evidence pass requires a
separate explicitly authorized implementation/test milestone. Milestone 6 is not started.
