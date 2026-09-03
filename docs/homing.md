# A6-RS positive-limit homing design

The selected strategy is `POSITIVE_LIMIT_REFERENCE`. PL serves as the positive travel
limit and the initial home reference; NL remains an independent negative travel limit.
An independent HSW and encoder-index refinement are deferred. Milestone 7 implements this
strategy only in domain state, authorization, deterministic simulation, and GUI display.
It does not implement real homing.

## Manual basis and drive responsibility

The supplied A6-RS position-mode manual describes drive-internal mode 18: search in the
positive direction for PL, reverse after the PL edge, and use the PL transition as the
home reference without a Z-pulse search. Mode 2 is similar but continues to a Z pulse.
This is family-level manual evidence. The installed drive model, firmware applicability,
active mode, input assignment, and parameters remain unverified.

Future real homing should use a verified drive-internal positive-limit method. Python may
eventually issue a reviewed high-level trigger and verify feedback. It must not generate a
real-time homing trajectory with repeated Jog commands or guess parameter writes.

## Required sequence

1. Require an active control lease, connected/fault-free state, Servo Enabled,
   `UNHOMED`, idle motion, and enabled configuration gates.
2. Reject contradictory PL/NL and PL already active. No automatic recovery search exists.
3. Search toward PL at the configured positive speed and within distance/time limits.
4. Detect PL and request a controlled stop; require stopped confirmation.
5. Reverse only as part of the authorized homing operation and require PL to clear within
   the configured backoff distance and timeout.
6. Continue negative by the configured nonzero home offset.
7. Stop, require PL inactive, verify stable completion, set the application reference,
   and only then enter `HOMED`.

The explicit phases are `SEARCHING_POSITIVE_LIMIT`, `CONTROLLED_STOP_AT_LIMIT`,
`BACKING_OFF_POSITIVE_LIMIT`, `APPLYING_HOME_OFFSET`, `VERIFYING_COMPLETION`, and
`COMPLETE`. Any failure enters `FAULT`; no restart, enable, resume, or motion follows
automatically.

## Rejection and fault behavior

The design rejects or faults on simultaneous PL/NL, PL active at start, PL not found,
search distance/time exhaustion, unconfirmed controlled stop, PL failing to clear,
backoff distance/time exhaustion, communication loss, drive fault, positive movement
while PL is active, a zero/missing offset, or an offset in the positive direction.
Timeout is not a substitute for physical PL/NL protection.

Homing requires configured positive search and backoff speeds and distances, positive
search direction, negative nonzero home offset, bounded timeouts, verified PL/NL polarity,
and verified installed support for drive-internal mode 18. Shared examples deliberately
leave these operational values zero or unverified, so future real homing fails closed.

Real homing additionally requires verified independent E-stop, STO or Servo Enable
removal, PL and NL operation, mechanical restraint, clear travel, direction, safe energy,
and an attended approved procedure. Homing alone does not establish angle calibration.
See [the commissioning plan](pl-homing-commissioning.md).
