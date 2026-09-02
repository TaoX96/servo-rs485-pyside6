# Repository development policy

## Authority and scope

This file is the highest-level development policy for the knee-rig repository. A nested
`AGENTS.md` may add stricter local constraints, but it must not weaken or override any
safety, hardware-access, process-isolation, or authorization requirement in this file.

Every milestone must remain within its explicitly approved scope. Do not begin a later
milestone, connect to hardware, or enable a more permissive operating mode without an
explicit user request.

## Final system architecture

- Windows runs only the PySide6 operator GUI. It sends validated high-level commands to
  the Raspberry Pi motion service and displays returned state and telemetry.
- The Raspberry Pi motion service exclusively owns the USB-to-RS485 serial device and is
  the only process permitted to communicate with the STEPPERONLINE A6-RS drive.
- The Raspberry Pi monitoring service owns camera, recording, file-management, health,
  and DS18B20 functions. It must not import or call the servo transport implementation.
- The A6-RS drive performs its servo loop, encoder processing, homing, acceleration and
  deceleration, and position trajectories internally.
- Emergency stop, STO or Servo Enable removal, and positive and negative travel limits
  form an independent hardware safety system. They must not depend on Windows, the Pi,
  Python, the GUI, networking, heartbeats, or RS485.

The motion and monitoring services are separate failure domains. Camera, recording,
temperature, file-management, or monitoring-service failure must not crash, restart, or
otherwise control the motion service. A GUI or monitoring failure must never cause motion
to start or resume.

PLC, LabVIEW, VISA, ActiveX, and MX Component are reference technologies only and must
not be introduced as dependencies unless the user explicitly changes the architecture.

## Mandatory safety rules

- Simulation is the default mode.
- Startup must never perform Servo On, homing, motion, or motion resumption.
- Pi startup or restart leaves the system `SERVO_DISABLED` and `UNHOMED`.
- A newly connected or reconnected GUI may initially read status only.
- RS485 reconnection must not enable the servo, home, resume, or recover motion.
- A timeout, malformed response, inconsistent feedback, invalid state, servo alarm, or
  unexpected condition transitions the service to `FAULT` or the connection to
  `COMMUNICATION_FAULT`/`DISCONNECTED`, stops new motion commands, and requires
  explicit operator recovery.
- Fault reset must not automatically enable the servo, home, or move.
- Automatic cycles and absolute-position moves are prohibited until homing succeeds.
- A controlled-stop command is not and must never be labelled as an emergency stop.
- Software travel limits supplement but never replace the physical PL and NL switches.
- Real automatic motion and homing are prohibited until the physical E-stop, STO or Servo
  Enable safety path, PL, and NL have been installed and verified.
- No heartbeat or network-disconnection response is a hardware emergency-stop function.
- Real-hardware testing must be attended. Do not perform unattended endurance tests.
- Never guess register addresses, types, signedness, scaling, word order, wiring, active
  levels, direction, units, safety behavior, or motion behavior.

On control-lease expiry during motion, the future motion service must request a controlled
stop when drive communication permits, reject further motion, enter `FAULT`, and require
explicit recovery. It must not automatically issue Servo Off: loss of holding torque has
not been mechanically validated.

## Process and I/O boundaries

- `src/knee_rig/gui/` contains Windows presentation and network-client behavior only. No
  GUI module may import MinimalModbus, pyserial, or a servo transport.
- `src/knee_rig/motion/` contains the Pi motion service, drive protocol, state machines,
  simulation, validation, and telemetry. Only this process may own RS485.
- `src/knee_rig/monitoring/` contains Pi camera, temperature, recording, and monitoring
  behavior. It must have no servo-driver dependency.
- `src/knee_rig/common/` contains shared, hardware-independent contracts and typed units.

Blocking serial, HTTP, video, file, sleep, or thread-join operations must not run on the
GUI thread. No module may initialize hardware or networking at import time. All I/O must
have bounded timeouts, cancellation behavior, and diagnostic context.

## Motion state requirements

Model service lifecycle, drive connection, servo enablement, homing, and motion as
orthogonal state dimensions rather than inferring them from UI state or elapsed sleeps:

- Service: `STARTING`, `READY`, `DEGRADED`, `FAULT`, `STOPPING`, `STOPPED`
- Connection: `DISCONNECTED`, `CONNECTING`, `CONNECTED`, `COMMUNICATION_FAULT`
- Servo: `SERVO_DISABLED`, `SERVO_ENABLING`, `SERVO_ENABLED`,
  `SERVO_DISABLING`, `SERVO_FAULT`
- Homing: `UNHOMED`, `HOMING`, `HOMED`, `HOMING_FAULT`
- Motion: `IDLE`, `STARTING`, `MOVING`, `PAUSED`, `STOPPING`, `MOTION_FAULT`

Transitions must depend on confirmed drive feedback. Keep pause, resume, controlled stop,
Servo Off, fault reset, and hardware E-stop indication distinct. Interrupted commands are
never resumed automatically. Finite cycling must execute bounded, confirmed operations
with a software-side completed-cycle counter; unbounded cyclic drive operation requires a
separately reviewed design.

## Network API policy

- Expose only versioned, allowlisted high-level commands with typed parameters.
- Validate every parameter and authorize every command against the state machine.
- State-changing requests require a UUID command ID and an active single-controller lease.
- Lease loss follows the controlled-stop and `FAULT` policy above.
- Do not expose a general-purpose endpoint that accepts arbitrary register addresses or
  values, even in operator mode.
- Separate normal operator commands from engineering operations. Engineering operations
  are disabled by default and require a deliberately enabled workflow.
- API request receipt is not evidence that a drive action completed; completion must be
  based on confirmed state and feedback.

## Configuration and persistent parameters

- Keep shared examples safe and machine-neutral. Never commit credentials, tokens, real
  network addresses, COM ports, or machine-specific `/dev/serial/by-id/...` values.
- Local overrides use `config/*.local.toml` and remain untracked.
- All safety capability gates default to false and simulation defaults to true.
- A missing or zero joint-angle calibration factor rejects angle-based motion.
- Motion limits remain zero/unconfigured until calibration and safety review approve them.
- Normal startup and reconnect must not write electronic gearing, DI assignments, homing
  settings, or any other persistent or machine-defining drive parameter.
- Persistent writes require a separate engineer-only workflow, Servo Off, a logged reason,
  explicit authorization, read-back verification, and configuration backup.

## Known communication baseline

The hardware-verification hypothesis is Modbus RTU, slave 1, 9600 baud, 8 data bits, no
parity, 1 stop bit, and a 1 second timeout. Legacy code used MinimalModbus and
`BYTEORDER_LITTLE` for 32-bit values. That order is unverified until a safe test confirms
it on the exact recorded drive model and firmware. Historical electronic-gear values 9
and 16384 are not a verified joint-angle calibration.

## Logging requirements

Use structured, timestamped logs for configuration snapshots, command IDs, lease events,
validated command parameters, state transitions, alarms, communication failures,
telemetry freshness, recovery confirmations, and completed cycles. Do not log credentials,
lease secrets, arbitrary image data, or unbounded response bodies. Safety-relevant events
must remain distinguishable from monitoring and media events.

## Testing and hardware authorization

- Unit and integration tests must use fakes or simulation and must not discover or open a
  serial port or access a Raspberry Pi.
- Hardware tests live only under `tests/hardware/`, carry the `hardware` marker, and are
  excluded from the default test command.
- No real hardware test may run without explicit user authorization for that exact test.
- Test startup must never enable, home, move, or write persistent parameters.
- Register codecs require signed, unsigned, boundary, negative, ordering, and read-back
  coverage before hardware use.

Expected local checks are:

```powershell
ruff check .
ruff format --check .
mypy src
pytest -q
```

`pytest -q -m hardware` is never part of routine verification and requires explicit user
authorization plus an approved hardware checklist.

## Development workflow for every task

1. Read `README.md`, `docs/requirements.md`, `docs/safety.md`,
   `docs/architecture.md`, `docs/register-map.md`, and relevant configuration and source.
2. Inspect existing changes and protected reference materials without running legacy code.
3. State the milestone, safety level, assumptions, and whether work is simulation-only or
   hardware-facing.
4. Make the smallest coherent change without broadening authorization.
5. Update tests and documentation for any interface or behavior change.
6. Run applicable formatting, linting, type, and test checks; report anything not run.
7. Report every changed or moved file, verification results, unresolved assumptions,
   reference-file preservation, and whether any hardware interface was accessed.

## Milestone 1 boundary

Milestone 1 implements only typed configuration and domain models, centralized command
authorization, a transport-free servo protocol, deterministic simulation, an in-process
coordinator, and hardware-independent unit tests. It does not implement a network server,
GUI, monitoring service, real servo driver, Modbus path, executable hardware Servo On,
real motion, real homing, systemd unit, or deployment script.

Do not open a COM port or `/dev/tty*`, access a Raspberry Pi or network service, import
legacy control code, install or start a service, write a drive parameter, commit, or push.
