# A6-RS homing design

This document records preliminary design conclusions. It does not confirm the installed
drive model, firmware, wiring, direction, register encoding, or safe commissioning state,
and it does not implement executable homing.

## Drive responsibility

Homing is performed internally by the A6-RS drive. Python may eventually configure an
approved homing setup through an isolated engineering workflow, trigger a reviewed
high-level homing command, monitor feedback, and verify the result. Python must not
simulate a homing trajectory using repeated Jog commands.

## Preliminary mode selection

- Mode 4 is the preliminary candidate when HSW is approached in the positive direction.
- Mode 6 is the preliminary candidate when HSW is approached in the negative direction.
- Modes 20 and 22 may be used during initial switch-edge and direction verification
  without Z-pulse searching.
- Mode 35 may be used only as a temporary commissioning zero.
- Mechanical hard-stop modes `-1` and `-2` are not recommended for this mechanism.
- Modes 33 and 34 must not be the only mechanical reference for the geared mechanism.

The final mode depends on the verified mechanical direction and installed positions and
active behavior of HSW, PL, and NL. These candidates must be checked against the exact
A6-RS model and firmware manual before any hardware test.

## Authorization gates

Real homing is prohibited until PL, NL, the physical E-stop, and the STO or Servo Enable
safety path are installed and independently verified. The exact drive and firmware,
switch wiring and active levels, approach direction, speed, acceleration/deceleration,
timeout, escape/reversal behavior, and safe test energy must also be approved.

Homing requires an explicit operator command, an active control lease, Servo Enabled,
`UNHOMED`, idle motion, enabled configuration gates, and state-machine authorization.
Startup, restart, reconnection, fault reset, or lease acquisition must never trigger it.

Electronic gearing and conversion between drive application units and joint angle remain
unverified. Homing does not make angle commands valid; angle motion remains rejected until
calibration is independently verified.

## Completion and failure

Homing succeeds only when all required evidence agrees:

- the drive reports homing completion;
- no drive or communication fault is present;
- speed is near zero using an approved threshold;
- the reported position is within the approved home tolerance;
- HSW, PL, and NL states are valid and consistent with the selected method; and
- feedback remains stable for the approved confirmation interval.

A bounded timeout is required but is not a substitute for PL/NL protection. Timeout,
contradictory feedback, unexpected switch state, alarm, lost communication, or an
out-of-tolerance result enters `FAULT` or `DISCONNECTED`, leaves homing unconfirmed,
blocks motion, and requires explicit recovery. No interrupted homing operation is resumed
automatically.

