# Requirements

## Milestone 4 scope

Milestone 2 retains the Milestone 1 typed configuration, shared models, centralized state
authorization, deterministic `FakeServo`, and idempotent in-process coordinator. It adds a
minimal PySide6 GUI that accesses the core only through a `MotionClient` abstraction and
an `InProcessSimulationClient`. Simulation progression uses a non-blocking Qt timer to
request explicit bounded ticks; the deterministic core remains independent of wall time.

The GUI displays orthogonal state, telemetry validity and explicit units, lease state,
central authorization outcomes, bounded event history, finite-cycle progress, and
simulation-only fault injection. It contains no HTTP/WebSocket transport, monitoring
implementation, real servo driver, Modbus communication, real Servo On, real homing or
motion, or systemd deployment. Milestone 3 additionally provides only pure register-word
encoding/decoding and immutable documentary register metadata. It adds no transport or
register access, and all runtime addressing and 32-bit hardware layout remain unverified.

Milestone 4 adds a one-shot offline symbolic reader, explicit read allowlists, an in-memory
synthetic-word transport, immutable typed results, and partial snapshots. No real transport,
writes, retry/polling loop, or GUI integration is added. Engineering inspection is disabled
by default. Catalog areas remain unresolved and synthetic fixture overrides cannot grant
hardware verification. Failures and ambiguous fields cannot become valid zero readings.

## System responsibilities

- Windows runs a responsive PySide6 GUI and communicates with Raspberry Pi services only
  through typed, timeout-bounded network clients.
- The Raspberry Pi motion service is the sole owner of USB-to-RS485 and all A6-RS Modbus
  RTU communication.
- The Raspberry Pi monitoring service independently provides camera, media, DS18B20, and
  Pi-health functions and must not depend on the servo transport.
- The A6-RS performs its servo loop, encoder processing, position trajectories,
  acceleration/deceleration, and drive-internal homing.
- Physical E-stop, STO or Servo Enable removal, and PL/NL switches provide independent
  hardware safety that does not depend on software or communication.

## Functional requirements for future milestones

- Provide health, motion-state, telemetry, and alarm queries.
- Provide validated high-level motion commands through an allowlisted API with command
  IDs, a single-controller lease, state-machine authorization, and explicit outcomes.
- Keep enable, disable, homing, single motion, finite cycling, pause, resume, controlled
  stop, and fault recovery distinct.
- Poll DS18B20 temperature and Pi health without affecting motion-service availability.
- Display video, capture images, record and download media, and manage experiment prefixes
  without blocking the GUI or sharing the motion-service process.
- Record configuration snapshots, commands, lease events, state transitions, alarms,
  telemetry freshness, and completed-cycle counts.

## State and recovery requirements

State is represented explicitly across service connectivity, servo enablement, homing,
and motion. Raspberry Pi startup begins `SERVO_DISABLED`, `UNHOMED`, and nonmoving.
Automatic cycling and absolute-position motion require confirmed `HOMED` state.

Startup, GUI connection, Pi restart, RS485 reconnection, fault reset, and service restart
must never automatically enable, home, start, or resume motion. A timeout, invalid state,
inconsistent feedback, servo alarm, or unexpected condition enters service `FAULT` or
connection `COMMUNICATION_FAULT`/`DISCONNECTED` and requires deliberate operator
recovery.

If the active GUI control lease expires during motion, the motion service requests a
controlled stop when communication permits, rejects further motion, enters `FAULT`, and
requires explicit recovery. It does not automatically issue Servo Off.

## Quality requirements

- GUI and monitoring failures cannot start, resume, crash, or restart motion control.
- Serial, HTTP, video, and file operations have exclusive ownership where applicable,
  bounded timeouts, cancellation, and structured diagnostics.
- Simulation is the default and supports hardware-independent unit and integration tests.
- Units are explicit and calibrated; a missing or zero angle conversion rejects motion.
- No general-purpose register-write API exists.
- Persistent drive parameters are never written during normal startup or reconnection.

## Open decisions and verification gates

- Exact A6-RS drive model, motor model, and firmware.
- Verified 16/32-bit data widths and 32-bit byte/word order.
- Joint-angle calibration, gearbox ratio, zero reference, and mechanical direction.
- Installed and verified E-stop, STO or Servo Enable path, PL, NL, and HSW wiring.
- Safe controlled-stop behavior and whether Servo Off can release the mechanism.
- Approved angle, speed, acceleration, deceleration, torque, temperature, and cycle limits.
- Authentication, transport security, network topology, and deployment addresses.
