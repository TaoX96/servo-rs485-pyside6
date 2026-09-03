# Hardware readiness — Milestone 7

Current safety level: **Controlled read-only commissioning preparation**. Milestone 7
provides a bounded diagnostic and machine-side checklists. No hardware was accessed and
no motion is authorized.

## Readiness gates

| Gate | Status | Meaning |
|---|---|---|
| A — Offline implementation | **PASS** | Codecs, allowlists, deterministic simulation, CLI framing/error paths, and cleanup are tested without hardware. |
| B — First raw read | **PREPARED / CONDITIONAL** | Documentation supports a narrow U16/FC03 request. Session 1 must still verify the installed path, identity, settings, disabled state, wiring, supervision, and exact authorization before opening the port. |
| C — Trusted physical telemetry | **BLOCKED** | No current Pi capture, installed applicability, freshness study, or PL/NL assignment/polarity verification exists. |
| D — Servo Enable/homing/motion | **BLOCKED** | Independent safety, mechanics, limits, calibration, safe motion parameters, qualified review, and drive-internal homing configuration remain unresolved. |

Gate B is not blocked by D-only questions such as joint calibration or future homing
speeds. Its conditional status does not authorize access by itself; the Session 1 stop
points and explicit authorization govern the actual one-shot read.

## Gate B item reassessment

The status terms below are intentionally source-specific. No item is marked verified on
current hardware.

| Item | Assessment | Basis / remaining action |
|---|---|---|
| A6-RS parameter read FC | **Confirmed by documentation** | Communication manual specifies FC03 for reading parameters. |
| U parameter address rule | **Confirmed by documentation** | Generic parameter rule uses group as address high byte and offset as low byte; parameter list supplies U labels. |
| `SERVO_STATUS` U41.0A, U16, RO | **Confirmed by documentation** | Selected first read at PDU address `0x410A`, one register. |
| `PLAN_OPERATION_GROUP` U41.08, U16, RO | **Confirmed by documentation** | Optional later read at `0x4108`. |
| `DI_STATUS` U40.04, U16, RO | **Confirmed by documentation** | Raw DI1-DI8 electrical levels at `0x4004`; bit/polarity interpretation remains installed evidence. |
| RTU byte order and CRC | **Confirmed by documentation** | Response word is high byte then low byte; CRC uses polynomial `0xA001`, low CRC byte first. |
| Slave 1, 9600, 8N1, 1 s | **Supported by historical operation** | Historical source and project material agree; current installed settings must be observed without changing them. |
| Drive/RS485 method worked | **Supported by historical operation** | User-confirmed successful LabVIEW operation and historical project/source evidence; not a current Pi capture. |
| Installed drive/model/firmware applicability | **Unresolved** | Record nameplate and display/version at Stop Points A/B. |
| Installed adapter and stable Pi path | **Unresolved** | Record label and exact `/dev/serial/by-id/...`; no discovery is built into the tool. |
| Current A/B/reference wiring and termination | **Unresolved** | De-energized inspection and qualified review. |
| Current Servo Disabled/restraint state | **Unresolved** | Confirm independently before any powered read. |
| Current PL/NL DI assignment and polarity | **Unresolved** | Observe assignment and stationary raw bit changes; never write settings. |
| Current Raspberry Pi raw frames | **Unresolved** | None captured in Milestone 7. |
| Joint calibration, homing parameters, motion limits | **Not required for first read-only test** | Required at Gate D, not for one stationary disabled-state status read. |
| HSW and encoder index | **Not required for first read-only test** | Deferred by selected PL-reference strategy. |

## Approved diagnostic shape

Only `SERVO_STATUS`, `PLAN_OPERATION_GROUP`, and `DI_STATUS` are compiled into the
diagnostic allowlist. `SERVO_STATUS` is the first candidate because it is a single U16,
read-only state value and does not require 32-bit layout or engineering interpretation.
The preview command opens no device. The armed command is Raspberry-Pi-only, uses the
exact local by-id path, sends one request, performs zero retries, captures the raw request
and response, reports stable errors, and closes the port.

`DI_STATUS` may follow only for the supervised stationary switch procedure. Its raw bits
do not prove switch semantics. Until installed DI numbers and active levels are verified,
the corresponding interpretation is `ACTIVE_LEVEL_UNVERIFIED`.

## Remaining evidence before execution

At Stop Point A record drive/motor/adapter identity, de-energized wiring, termination,
shielding, PL/NL mounting and terminals, contact type, DI assignment evidence, available
Servo Enable removal, restraint, and clear travel. At Stop Point B record displayed
firmware/settings, Servo Disabled evidence, the exact Pi device path, sole ownership, and
the reviewed request preview. A qualified person must address any enclosure or electrical
safety work; do not open an energized enclosure or touch live conductors.

At Stop Point C preserve results and review them before proposing any later access.
Completion of Session 1 does not authorize motion.
