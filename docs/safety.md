# Safety and commissioning gate

This software is supervisory control software. It is not a safety controller, and no
Python, GUI, Modbus, API, watchdog, or heartbeat action is safety-rated.

## Emergency stop and controlled stop

A hardware emergency stop must remove motion-producing capability through an independently
designed and verified electrical path. It must work without Windows, Raspberry Pi,
software, networking, or RS485.

A controlled stop is a normal drive command that attempts a bounded deceleration while
communication and drive control remain available. It may fail during power, drive,
communication, or software faults. The GUI must label it **Controlled stop**, never
Emergency stop or E-stop.

Automatically issuing Servo Off after a controlled stop is not currently permitted because
loss of holding torque could allow unsafe mechanism movement. That behavior requires
mechanical and electrical review.

## Independent hardware safety boundary

- The E-stop and STO or Servo Enable removal path must independently prevent torque or
  motion as defined by the qualified electrical safety design.
- Physical positive and negative travel switches, PL and NL, must prevent travel beyond
  the safe mechanism range without relying on software limits.
- The selected future homing reference is PL itself. Its position, input assignment,
  active level, positive approach direction, stop behavior, release distance, and
  relationship to NL must be verified. An independent HSW is deferred.
- Software angle and travel limits are supplementary protections only. They do not replace
  PL, NL, safe mechanics, or the E-stop/STO path.
- A qualified person must review and approve the final electrical safety circuit, wiring,
  safety functions, risk assessment, and commissioning procedure.

## Permitted before safety hardware is installed and verified

- Documentation, architecture, code review, and configuration design.
- Simulation-only development and hardware-independent automated tests.
- Static inspection of manuals and legacy evidence without executing control code.
- Design and offline validation of read-only diagnostics.
- After separate authorization, one supervised, one-shot, allowlisted read while powered
  but Servo Disabled, following the Session 1 stop points. This grants no motion authority.

## Prohibited before safety hardware is installed and verified

- Real Servo On, homing, Jog, position motion, cycling, or motion recovery.
- Real automatic motion or unattended hardware/endurance testing.
- Persistent or machine-defining drive parameter writes.
- Direction, switch, or homing tests that could create motion.
- Treating a network heartbeat, GUI action, software limit, or drive command as an E-stop.

## Pre-motion inspection checklist

Real motion remains prohibited until all applicable items are recorded and approved:

- [ ] Exact drive, motor, and firmware are recorded.
- [ ] Wiring diagram matches the installed machine and has qualified review.
- [ ] Mechanical load, gravity, stored energy, pinch points, guarding, and safe test energy
      are assessed.
- [ ] Physical E-stop operates independently of the PC, Pi, network, and RS485.
- [ ] STO or Servo Enable removal behavior is verified, including loss of holding torque.
- [ ] PL and NL stop travel in the intended directions and cannot be bypassed by software.
- [ ] PL's dual role as positive limit and reference is reviewed; assignment, polarity,
      approach, stop, release, repeatability, and negative home offset are verified.
- [ ] Operator can reach the E-stop and maintain a clear exclusion zone throughout testing.
- [ ] USB-RS485 adapter, isolation, termination, grounding, and cable routing are recorded.
- [ ] Slave address and serial settings are verified using an approved read-only procedure.
- [ ] Register width, signedness, scale, and 32-bit byte/word order are verified.
- [ ] Electronic gearing is read back; it is not changed during normal startup.
- [ ] Joint-angle conversion, zero, gearbox ratio, and positive direction are calibrated.
- [ ] Conservative angle, speed, ramps, torque, temperature, and cycle limits are approved.
- [ ] Controlled stop, alarm, timeout, cable removal, power loss, and restart behavior have
      approved low-energy test procedures.
- [ ] Startup and every reconnect path are shown not to enable, home, move, or resume.

## Fault and reconnection behavior

A timeout, malformed response, inconsistent feedback, invalid state, servo alarm, or other
unexpected condition transitions the service to `FAULT` or the connection to
`COMMUNICATION_FAULT`/`DISCONNECTED`.
Recovery requires explicit operator confirmation. Fault reset, Pi restart, GUI reconnect,
RS485 reconnect, and lease reacquisition must never automatically enable, home, resume, or
move.

If a GUI control lease expires while moving, software requests a controlled stop when
communication permits, blocks further motion commands, and enters `FAULT`. This response
is not an emergency stop and does not replace the independent hardware safety system.

No real hardware test may be unattended or run without explicit authorization for that
test. Commissioning must proceed through separately reviewed, bounded, low-energy stages;
this document does not authorize any such stage.

Milestone 7 permits preparation for a controlled read-only session only. Completion of
Session 1 does not authorize Servo On, Fault Reset, homing, or motion.
