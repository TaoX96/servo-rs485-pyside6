# Future read-only commissioning design

**Design only; not executed. Current safety level: Simulation.** Gate B and Gate C are
blocked in [hardware-readiness.md](hardware-readiness.md). This document is not authority
to implement a transport, discover devices, connect a Pi, open a port or read a drive.
No executable commands, adapter skeleton or configuration enabling hardware are supplied.
Every hardware-facing phase needs its own explicit user authorization, qualified safety
review and a stop-at-first-unexpected-result procedure. Read-only permission never grants
enable, reset, homing, motion, writes, automatic recovery or deployment permission.

## Phase 0 — documentation confirmation

Future evidence intake can remain entirely offline. Match exact drive/motor/adapter
identity to manufacturer documents and firmware applicability. Obtain the complete
communication manual; resolve read FC, framing, CRC, timing and address notation. Review
existing communication-setting records rather than assuming defaults. If new keypad
observations are necessary, require separate powered-observation authorization, an
accessible external display and safe disabled/restraint review; never change a parameter.
Qualified wiring review uses existing schematics or approved power-isolated inspection,
not an energized enclosure. Obtain a safe energization/inhibition and load-restraint plan.

Exit: reviewed Gate B evidence package, including selected harmless read or an explicitly
bounded address-candidate plan. Missing identity, unsafe access or ambiguous protocol
means stop; do not compensate with device scans or read-function guesses.

## Phase 1 — Pi environment observation (future hardware-facing work)

Separate authorization is required even for read-only host observation. Record the exact
board, OS, architecture, Python runtime, power supply and USB topology; inspect the
existing stable `/dev/serial/by-id/` identity and relevant ownership/group permissions.
Confirm no other process owns the adapter and document that the future Pi motion-service
identity will be its sole owner. Do not open the serial endpoint to identify it, start a
service, change permissions, install packages or use network/device scanning as part of
observation. An absent/non-unique by-id identity blocks further work pending reviewed
identity design; do not substitute a transient device name.

Exit: exact host/adapter ownership record and explicit approval to proceed to offline
implementation. Nothing is installed, enumerated or contacted in Milestone 5.

## Phase 2 — offline concrete-adapter implementation (future code milestone)

Only after the Gate B evidence/design review and explicit coding authorization, implement
a read-only concrete transport inside the Pi motion ownership boundary. Expose no writes,
generic execution, arbitrary operator addresses or motion connection. Keep real device
access disabled by configuration. Use a fixed symbolic allowlist and explicit verified
mapping, strict frame/CRC/exception/length validation, a bounded timeout and request count,
zero automatic retry, and cancellation/close behavior. No polling or reconnect loop.

Test with in-memory fake serial bytes or a software-only loopback fixture, not a physical
adapter. Prove all rejected/malformed/timeout paths fail closed and cannot send writes or
trigger state transitions. Existing synthetic fixture validity cannot become hardware
verification. Review offline test results and the physical-test checklist independently.
No such adapter, skeleton, fixture expansion or dependency change is added by Milestone 5.

## Phase 3 — first authorized physical read (future hardware-facing work)

Do not select the first register yet. A candidate must be an independently observable,
harmless U16 status value supported by the exact manual's FC, area, address convention,
read conditions and lack of read side effects. The historical `0x410A` constant alone
does not qualify it; neither does membership in the current offline operational allowlist.

Before the test, record explicit authorization naming the exact device, register label,
FC, address/base/area, count **one 16-bit word**, timeout, adapter/host, expected display
value and stop procedure. The timeout must be finite and justified by the matched manual;
there is no guessed default in this design. Independent approved means must prevent
unexpected mechanical hazards with the servo disabled. Check gravity/brake behavior;
never rely on unverified self-locking, software status or communication success for safety.

An authorized operator remains present. Permit **one request total**, one outstanding
request, **zero automatic retries**, no broadcast, no background poll, no GUI integration
and no write/motion path. Capture full request/response bytes and independent display
context. End the session after success **or the first error**; close the transport and
retain the evidence. A response is not yet a verified address or trusted telemetry.
No Servo On, Servo Off toggle, fault reset, homing, parameter write or power-cycle recovery
is part of this test. Unexpected motion/state is an immediate safety stop condition.

## Phase 4 — interpretation validation (future hardware-facing work)

Separately authorize a bounded list of fields and repeat count before each session;
there is no default polling loop. Compare raw U16 words against independently recorded
keypad state and confirm 16-bit wire interpretation. Observe status transitions only if
they arise in separately approved safe non-motion conditions; do not enable or reset the
servo to create a transition. If an independent comparison is unavailable, leave the
field unverified rather than forcing a state change.

For I16, confirm signed representation/scale from compatible evidence and independent
observations; do not cause motion or unsafe loads to obtain a negative sample. For 32-bit
values use the static procedure below. Review timestamp/freshness, plausibility and
repeatability per field. Trusted interpretation is separate from raw acquisition and
never authorizes an angle conversion, home claim or motion.

## Phase 5 — bounded read-only soak (future hardware-facing work)

Requires a separate approved duration, polling frequency, maximum total requests and
timeouts, selected read allowlist, attended operator and stop criteria. No unbounded or
unattended endurance run. No motion, writes, auto-reset, auto-retry storm or automatic
reconnection. Stop at the first unexpected exception, stale/contradictory sample, loss of
connection or safety-state change. Review communication-error logs without filling failed
readings with zeros or stale cached values. A later authorized reconnect starts a new
session and cannot change servo/homing/motion state or resume prior activity.

## Address-verification design

This is a separate future procedure if exact documentary mapping still needs a bounded
verification, not an automatic fallback within the first-read test.

1. Start from exact compatible manual evidence for a harmless, independently observable
   U16 status label and known read FC. If the manual does not support safe candidates, stop.
2. Record a **maximum of two explicitly named evidence-derived candidates**, including the
   notation, proposed PDU address and why each is plausible. No formula or implicit
   plus/minus-one transformation is authorized by this document.
3. Review each candidate for harmless read access and absence of trigger/write-only
   behavior. Obtain explicit approval for the first candidate's one-request session.
4. Send at most one request for that candidate, capture bytes and independent expected
   value, then close. Stop on the first exception, unexpected length/value or inconsistency.
   Do not continue to a second candidate after an error as a recovery technique.
5. Review the result. A valid response alone does not establish a mapping; it must agree
   with independently expected status semantics. Coincidental zeros or indistinguishable
   values remain inconclusive. Repeatability needs a separately approved validation session.
6. A second candidate is permissible only after review of a non-error result and **new
   explicit user approval**. Never scan a range, automatically increment/decrement an
   address, switch FC, change station/baud, or probe write-only/trigger registers.

Record a field-specific conclusion; never extrapolate one successful mapping across
parameter groups or monitor areas without supporting documentation.

## 32-bit-layout verification

Future-only, after the selected field's raw-read prerequisites are approved. Prefer a
static machine-configuration value independently displayed by the drive keypad or a
trusted, separately authorized commissioning display. Engineering inspection needs
explicit permission and stays read-only. Do not connect a commissioning tool under the
authority of this design. Do not write a convenient value or change electronic gearing.

1. Confirm label/address/FC, width, signedness, scale and coherent two-word read semantics.
   Record the exact display value/unit and active C0A.06 setting if independently available.
2. Under a bounded approved read session capture the two original 16-bit words and full
   wire bytes, with byte-to-word assembly explicitly documented.
3. Offline, evaluate all four codec combinations: BIG/HIGH_WORD_FIRST,
   BIG/LOW_WORD_FIRST, LITTLE/HIGH_WORD_FIRST, LITTLE/LOW_WORD_FIRST. Record decoded
   integers and any documented scale application separately; application units are not degrees.
4. Compare every candidate with the independent static value. Require a unique plausible
   match. Zero, repeated bytes or symmetric words can make layouts indistinguishable;
   if multiple candidates remain plausible, keep the result unverified and stop for review.
5. Repeat the static read only within a separately approved finite request budget; require
   consistent raw words and independent context. No moving-position-only verification.
6. Record exact drive model/firmware, register, raw words, expected display value, all four
   outcomes and selected layout or unresolved result. Reviewer approval is required before
   any future physical verification classification; none is granted by Milestone 5.

Do not promote one register's layout globally without evidence that the drive applies it
consistently to the relevant registers and settings. Record byte positions explicitly;
MinimalModbus names and other documentation may define "little endian" differently.
P's C0A.06 low-word-first default is not a verified active layout. The speed-width conflict
must be resolved separately; layout testing cannot resolve an unknown request width by guess.

## Stop conditions and rollback

Stop on unexpected response/exception, CRC/length/slave/FC mismatch, timeout, disconnect,
contradictory or stale data, unexpected servo state, any motion, unsafe mechanical condition,
loss of operator supervision, ambiguous ownership, or an authorization mismatch. Do not
retry, switch settings, widen the allowlist or issue corrective drive commands.

Cancel/close the future transport without new commands, preserve logs/raw evidence and
mark the session stopped/unverified. Closing communication is not a physical emergency
stop. For a physical hazard use the approved independent hardware safety procedure with
the qualified operator; never substitute software controlled stop or assume torque removal
is mechanically safe. The approved restraint and energy-isolation procedure governs any
physical disconnection. Do not unplug or touch live wiring as software rollback.

Because this workflow writes nothing, it has no parameter-restore operation. Do not issue
reset, Servo Off, brake release or power-cycle commands to restore a "known" state. Do not
automatically reconnect, enable, home, resume or recover. A later session requires a new
review and explicit authorization; simulation state must never be mistaken for drive state.

## Recording template

Use a future sanitized record with every field completed or explicitly `unknown`. An
incomplete capture cannot establish physical verification. Retain originals with controlled
access; do not record credentials, tokens or unnecessary full serial numbers.

| Field | Required record |
|---|---|
| Authorization | Procedure/revision; approving user and qualified reviewer; date; exact request budget and timeout; attended operator |
| Device | Drive and motor model; private device identity reference; firmware and communication versions; manual title/revision/pages and applicability |
| Safe conditions | Disabled-state evidence independent of response; restraint/brake/energy review; safety operator; expected state; stop/close procedure |
| Host / adapter | Pi OS/architecture/Python; exact adapter/revision; sanitized stable identity; sole owner; approved wiring/topology evidence |
| Active settings | Station, baud, data bits, parity, stops, response delay, relevant data-format setting; observation source/date; no defaults substituted |
| Selected read | Symbol/manual label, documented area, FC, exact address, address notation/base/mapping source, approved count; no arbitrary fallback |
| Timing / freshness | UTC request/response/display timestamps; monotonic elapsed/age; sequence; validity and planned maximum age |
| Wire evidence | Original request bytes; original response bytes; explicit CRC inclusion/exclusion, validation result and frame boundaries |
| Independent expectation | Keypad/display photo or record, label, value, unit and observation conditions; why independent and static |
| Raw / interpretation | Original word order and two 16-bit words where applicable; byte assembly; primitive/signedness/scale; all four layout results; unique match or unresolved |
| Outcome | Actual bytes/count/state; errors/timeouts; plausibility/repeatability; per-field documentary versus physical conclusion; no blanket layout promotion |
| Closure | Transport closed; no retry/write/motion; evidence retained; reviewer decision and separately authorized next step, if any |

No genuine capture is currently available. This template and plan do not themselves supply
evidence, confer hardware readiness or begin Milestone 6.
