# Positive-limit homing commissioning design

Selected strategy: `POSITIVE_LIMIT_REFERENCE`. PL is both the positive travel limit and
initial homing reference; NL remains the independent negative travel limit. A separate HSW
and encoder-index refinement are deferred. This is simulation and future commissioning
design only. It does not authorize Servo On, Fault Reset, homing, motion, or parameter writes.

## Manual evidence and current limitation

The A6-RS position-mode excerpt, PDF pp. 35-41 (printed 92-98), defines homing parameters
and limit-based modes. Mode 2 searches forward for PL, stops, reverses until PL clears, and
then searches for Z. Mode 18 is explicitly "similar to mode 2" but uses the PL OFF-to-ON
position as home without searching for Z. `C10.0B` defines the home-to-zero offset. This is
strong family-manual evidence for a drive-internal positive-limit strategy without an HSW
or Z refinement. Exact installed model, firmware support, parameter values, signs, units,
input assignments, and active levels remain unverified; no C10 write is implemented.

Historical successful control through LabVIEW/Python, MinimalModbus, the Waveshare adapter,
and the custom RJ45 cable supports that the RS485 method previously operated. It is not a
current Raspberry Pi capture or proof of current wiring, input assignments, or mode 18.

## Required future sequence

The future motion service remains the sole RS485 owner and should invoke the reviewed
drive-internal homing operation rather than synthesize a real-time jog loop.

1. Require an active single-controller lease.
2. Require connected, fault-free state, Servo Enabled, idle motion, and unhomed state.
3. Reject contradictory PL/NL and reject PL active at start until a separate recovery
   sequence is defined and approved.
4. Start a bounded positive PL search using verified speed, acceleration, timeout, and
   maximum distance.
5. Detect PL and require a confirmed controlled stop.
6. Reverse in the negative direction inside the active homing operation only.
7. Require PL to clear within the verified backoff distance and timeout.
8. Move farther negative by the non-zero, negative home offset.
9. Require stopped, stable, fault-free completion with PL inactive.
10. Set/accept the application reference and enter `HOMED` only after every condition passes.

Simulation exposes the phases `SEARCHING_POSITIVE_LIMIT`, `CONTROLLED_STOP_AT_LIMIT`,
`BACKING_OFF_POSITIVE_LIMIT`, `APPLYING_HOME_OFFSET`, `VERIFYING_COMPLETION`, and
`COMPLETE`. Ordinary positive movement remains rejected while PL is active. Negative
backoff is represented only inside the authorized homing operation.

## Fail-closed outcomes

Any simultaneous PL/NL, missing PL before distance limit, search timeout, PL active at
start, PL failing to clear, backoff timeout, wrong/zero offset, communication loss, drive
fault, or unconfirmed controlled stop enters a fault outcome, leaves the application
unhomed, stops progress, and requires explicit recovery. Startup, reconnect, lease
reacquisition, or fault reset never restarts homing, enables the servo, resumes, or moves.

## Parameters that must be collected and reviewed

- Exact installed drive model, firmware, and confirmation that internal mode 18 applies.
- Installed PL and NL DI numbers, contact types, active levels, filtering, and direction.
- Positive motor/mechanism direction and safe relationship between PL and mechanical stop.
- Search and backoff speeds, acceleration/deceleration, maximum distances, and timeouts.
- Non-zero negative home offset in documented application units and its safe final position.
- Controlled-stop completion feedback, stable-completion criteria, and repeatability tolerance.
- Independent E-stop, STO/Servo Enable removal, physical PL/NL action, restraint, brake,
  gravity, guarding, and qualified electrical/mechanical review.

All committed example values remain disabled or zero/unconfigured. The family-manual mode
number is recorded as 18 while installed applicability remains false. Persistent homing and
DI configuration require a later engineer-only, Servo Off workflow with explicit
authorization, backup, read-back, and a logged reason.
