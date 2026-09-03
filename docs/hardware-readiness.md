# Hardware readiness — Milestone 6 reassessment

Current safety level: **Simulation**. This is a documentation/evidence audit, not a
hardware test. No real adapter, adapter skeleton, connection, device discovery, register
read/write or deployment exists as a result of Milestone 6. Real enable, homing and motion
remain prohibited. Readiness is assessed from the [evidence matrix](evidence-matrix.md),
not from assuming that historical code still describes the rig.

## Gate decisions

| Gate | Current result | Evidence / outstanding decision |
|---|---|---|
| A — Offline codec readiness | **PASS** | Committed Milestone 4 (`0031e4b`); pure codecs, conservative catalog, fake transport, allowlists, ambiguity preservation and offline tests. Entry checks: Ruff and format pass, mypy 32 source files, pytest 164 passed. Only synthetic behavior is demonstrated. |
| B — Real raw read readiness | **BLOCKED** | A6-RS family evidence establishes FC03 and C-parameter group/offset framing, but installed target/firmware, adapter/wiring/settings, U-monitor mapping, harmless read conditions and safe disabled/restraint evidence remain unresolved. |
| C — Trusted typed telemetry readiness | **BLOCKED** | B plus speed width, active C0A.06 word order, U mapping, independent observations, plausibility/freshness and repeatability remain unverified. |
| D — Motion readiness | **BLOCKED** | Independent safety, PL/NL, HSW, homing, joint calibration, direction, travel limits, holding/brake behavior and qualified review unresolved. |

Passing A grants **no hardware permission**. Milestone 6 does not pass B. Passing B would
establish evidence readiness only, not permission for a read or trusted interpretation.
Gate B evidence readiness does not authorize hardware access. A separate implementation
milestone and a separate explicit first-read authorization are still required. Passing C
does not grant motion permission. No gate changes configuration, state, lease, homing or
servo enablement automatically.

### Gate A acceptance

Retain strict U16/I16/U32/I32 validation, signed/boundary/negative vectors and all four
explicit layouts; preserve raw words and documentary metadata. Symbolic allowlists remain
immutable; engineering reads remain disabled by default; displacement is not allowlisted.
Unknown area/address/layout and malformed responses fail closed. Speed ambiguity must
not become trusted telemetry. Fake checksums are injected failures, not real RTU CRC tests.
No source/test changes are needed for this audit.

### Gate B mandatory-condition reassessment

| Mandatory condition | Result | Evidence / remaining blocker |
|---|---|---|
| Exact target drive identity | **BLOCKED** | Manual model tables/sample nameplates are not an installed nameplate; firmware unknown |
| Manual applicability | **PARTIAL** | N1-N4 cover A6-RS family/listed models, but installed model/firmware cannot be matched |
| Adapter identity | **PARTIAL** | N5 matches the historical product illustration; installed label/revision unverified |
| Physical interface compatibility | **PARTIAL** | N2/N5 document RS485 +, -, GND; custom cable/electrical suitability unverified |
| Wiring evidence | **BLOCKED** | No current isolated as-built wiring, grounding, termination or bias evidence |
| Current communication settings | **BLOCKED** | No current record; defaults and legacy 9600/8/N/1 are not installed values |
| Read function code | **PARTIAL** | FC03 explicit for C parameters; U monitor/status, I/O and alarm behavior unresolved |
| Register area | **PARTIAL** | C group/offset defined; U areas not mapped |
| Address convention | **PARTIAL** | C label-to-PDU mapping needs no +/-1; U and library conventions unresolved |
| First harmless U16 candidate | **BLOCKED** | U41.0A lacks explicit U mapping/read-condition evidence; catalog C candidates are RW configuration |
| Servo-disabled condition | **BLOCKED** | No current independent state/restraint evidence; N1 lists `Reading disabled` without condition mapping |
| Request timeout | **PARTIAL** | Bounded timeout required; exact justified value/current response setting unresolved |
| Retry policy | **PASS** | Future design fixes retries at zero |
| Request count bound | **PASS** | Future design fixes one request, one U16 word and one outstanding request |
| Read allowlist | **PASS** | Existing symbolic allowlist; this does not validate its addresses |
| Capture plan | **PASS** | Full bytes, CRC/context and independent-observation template defined |
| Explicit authorization | **PASS** | Separate implementation and exact first-read authorization required |
| Stop after first unexpected result | **PASS** | Close and retain evidence; no fallback, retry or settings change |

Overall Gate B is **BLOCKED** because every mandatory condition must pass. Documentary
progress on FC03/C addresses cannot compensate for missing installed-device, U-status,
wiring/settings and safe-test evidence.

### Gate B acceptance — requirements retained for future reassessment

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
- Confirm the harmless read function code for the chosen area. FC03 is supported for
  documented C parameters, but U monitor/status mapping remains open; guessing FC04 or
  extending the C rule is not a substitute.
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

## Remaining evidence request by gate

Start with existing files and safely accessible exterior labels. These are information
requests, **not permission to power equipment, open an energized enclosure, touch live
wiring, connect a commissioning tool, change a parameter or test a brake**. If access needs
isolation or enclosure opening, stop and use a qualified person and approved isolation
procedure. Separately authorize any powered observation. Redact serial numbers, asset IDs,
hostnames and private network details; credentials, tokens and private keys are not needed.

### Gate B blockers — smallest remaining set

| Priority | What / usual location | Why needed | Power / read-only / qualification / redaction |
|---|---|---|---|
| 1 | Current drive nameplate and firmware/version record, plus a complete communication section explicitly mapping U monitor/status reads | Match the supplied chapters to the installed drive and resolve U41.0A FC/area/address/read conditions | Exterior label/existing record can be unpowered/read-only; any new display observation needs separate powered authorization and approved restraint. Qualified person if enclosure access is needed. Redact serial number. |
| 2 | Current adapter front/back label and existing as-built schematic or isolated RS485 +, -, GND/PE/custom-cable evidence | Match N5 to the installed revision and confirm grounding, termination/bias and exact safe wiring | Unpowered files/photos preferred. Isolate equipment; qualified electrical person for wiring/enclosure inspection. No rewiring. Redact asset IDs. |
| 3 | Existing current C0A.00/.01/.02/.03/.06 records and independently recorded Servo Disabled/safe-energization and gravity/brake restraint review | Establish installed settings, timeout basis and the safe non-motion precondition | Existing records need no power. New keypad/state observation is powered, read-only, separately authorized and attended; qualified safety/electrical review required. Change no parameter. |

### Gate C blockers

- Applicable manufacturer evidence resolving U40/U41 addressing and the U40.01
  I16-versus-32-bit conflict. Supplying documents needs no equipment power.
- Existing current C0A.06 setting and independent static display values for each proposed
  field. New observations are powered/read-only and require the same separate authorization,
  restraint and qualified review as Gate B. Do not change values.
- Later, separately authorized bounded repeatability/freshness captures. No capture is
  requested or permitted in Milestone 6.

### Gate D blockers

- Existing qualified electrical/mechanical review and as-built E-stop,
  STO/enable/contactor, PL/NL/HSW, brake and gravity-load documentation.
- Installed gearbox/coupling, direction, hard stops, safe travel, zero and calibration
  evidence. Prefer existing records/unpowered isolated photos; no energized inspection,
  switch test or motion is requested.
- Redact serials/asset identifiers. Qualified personnel are required for enclosure,
  wiring and safety conclusions. None of these requests authorizes motion.

## First-read candidate decision

**No first-read candidate can yet be approved.** `SERVO_STATUS` / U41.0A remains the
preferred type because the parameter table describes it as U16, read-only, raw status 0-3,
meaningful without motion and independently displayable. N1 does not explicitly map U
labels or establish their FC/area/address/read conditions or lack of side effects.
Therefore `0x410A`, FC03 and one word cannot be approved as a physical request. No C entry
in the current catalog is both documentary read-only and harmless status.

## Smallest safe next milestone

Milestone 7 proposal: **offline closure of remaining Gate B evidence only**. Review the
three Gate B evidence packages above and reassess the exact U16 candidate. Do not implement
an adapter, discover devices, connect hardware, change settings or read a register. Gate B
remains blocked unless every mandatory condition passes. Milestone 7 is not started.
