# Requirements

## Milestone 1 scope

Milestone 1 provides typed layered configuration, serializable shared models, centralized
state authorization, a hardware-independent servo protocol, deterministic `FakeServo`,
and an in-process motion coordinator with command idempotency. Simulation operations use
explicit ticks and never sleep or access hardware or networking.

It contains no HTTP server, GUI, monitoring implementation, real servo driver, Modbus
communication, real Servo On, real homing or motion, or systemd deployment.

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
