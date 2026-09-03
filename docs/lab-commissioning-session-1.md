# Laboratory commissioning session 1 - read-only

Safety level: **Controlled read-only commissioning preparation**. This checklist permits
only an attended, stationary, Servo Disabled observation session. It does not authorize
Servo On, Fault Reset, homing, motion, a register write, or opening or touching an energized
enclosure. A qualified person controls electrical isolation and the independent safety path.

Use [the observation record](lab-observation-record.md). Stop on any unexpected state,
motion, alarm, contradictory limit indication, malformed response, CRC error, timeout,
uncertain wiring, loss of supervision, or inability to confirm Servo Disabled. Close the
diagnostic after its single request; do not retry, scan, change settings, reset a fault, or
continue to another register until the result has been reviewed.

## Stop Point A - de-energized inspection

Equipment is isolated under the laboratory procedure. Do not open an energized enclosure
or touch live conductors.

- [ ] Record drive and motor nameplates and firmware record; redact full serials in shared notes.
- [ ] Record the adapter model and revision.
- [ ] Record RS485 A/B/GND or reference wiring, termination, shielding, and cable route.
- [ ] Record PL and NL mounting, mechanical actuation, wiring terminals, and contact type.
- [ ] Record the installed drive DI assignment for PL and NL. Do not change it.
- [ ] Record the available physical Servo Enable/STO removal method and qualified review.
- [ ] Confirm mechanical restraint and a clear travel/exclusion area.
- [ ] Record station, baud, data bits, parity, stop bits, response delay, and exact
      `/dev/serial/by-id/...` path from existing approved records.

**STOP A:** a qualified reviewer checks the record. If any item needed for safe energization,
stationary switch operation, or the exact read is unresolved, end the session.

## Stop Point B - powered, Servo Disabled, stationary

Do not allow Servo On at this stop point. Do not move the mechanism under power to test a
switch. Confirm Servo Disabled independently from the Modbus response and retain the
mechanical restraint.

1. Copy `config/pi.example.toml` to the ignored `config/pi.local.toml` and enter only the
   reviewed local device path and installed communication values. Leave all enable, motion,
   homing, and write gates false. Record PL/NL DI numbers only if the installed assignments
   are known. Keep each active level `unverified` until this session establishes it.
2. Confirm only the already recorded path; do not enumerate or discover serial devices:

   ```bash
   readlink -f /dev/serial/by-id/REVIEWED_DEVICE_NAME
   ```

3. Preview the exact first request without opening the device:

   ```bash
   python -m knee_rig.motion.diagnostics validate-config --config config/pi.local.toml --register SERVO_STATUS
   ```

   For station 1 the planned bytes are `01 03 41 0A 00 01 B0 34`. Review the configured
   path, station, serial format, timeout, register, FC03, word count, and request CRC.
4. After the attending user explicitly authorizes that exact read, run one request:

   ```bash
   python -m knee_rig.motion.diagnostics read --config config/pi.local.toml --register SERVO_STATUS --arm-read-only-hardware
   ```

   Save the JSON result, including UTC/monotonic times, request/response bytes, CRC result,
   raw value, Modbus exception, stable error code, and `port_closed` state. This status value
   does not prove STO, restraint, or safe holding torque.
5. If and only if the first result is non-error and reviewed, preview and explicitly approve
   each later one-shot request separately. `PLAN_OPERATION_GROUP` is optional:

   ```bash
   python -m knee_rig.motion.diagnostics validate-config --config config/pi.local.toml --register PLAN_OPERATION_GROUP
   python -m knee_rig.motion.diagnostics read --config config/pi.local.toml --register PLAN_OPERATION_GROUP --arm-read-only-hardware
   ```

6. Observe PL/NL while the mechanism remains stationary. Run one explicit `DI_STATUS` read
   at each condition, reviewing the result before the next action:

   ```bash
   python -m knee_rig.motion.diagnostics validate-config --config config/pi.local.toml --register DI_STATUS
   python -m knee_rig.motion.diagnostics read --config config/pi.local.toml --register DI_STATUS --arm-read-only-hardware
   ```

   Record, in order: neither switch actuated; PL manually actuated; PL released; NL manually
   actuated; NL released. The output always retains `raw_value` and DI1-DI8 raw levels. Until
   polarity is verified it reports `ACTIVE_LEVEL_UNVERIFIED`. Do not physically activate PL
   and NL simultaneously; contradiction handling is checked in simulation unless a separate
   qualified assessment establishes that simultaneous stationary activation is safe.

**STOP B:** close the session immediately after the planned finite reads. Do not retry an
error or use another function, address, station, baud rate, or device.

## Stop Point C - review

- [ ] Confirm every invocation sent no more than one request and the port closed.
- [ ] Compare raw frames with the planned register, station, length, function, and CRC.
- [ ] Classify each fact as documentation, historical operation, current hardware, or unresolved.
- [ ] Record the observed PL/NL DI bit changes and leave polarity unresolved if evidence conflicts.
- [ ] Archive the sanitized record and genuine raw captures without credentials or full serials.
- [ ] List every unresolved item before proposing a later authorization milestone.

**Completion of Session 1 does not authorize motion.**
