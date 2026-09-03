# Knee Rig Control

This repository defines a distributed control and monitoring system for a knee-test rig.
The intended operator interface is a PySide6 application on Windows, while a Raspberry Pi
will own motion communication and monitoring services. The project is currently at
**Milestone 7: laboratory commissioning preparation and positive-limit homing design**.
Current safety level: **Controlled read-only commissioning preparation**.

Milestone 2 adds a minimal PySide6 operator shell and a high-level motion-client boundary
over the Milestone 1 deterministic simulation. It exercises state presentation, command
authorization, leases, simulated enable and homing, bounded application-unit motion,
finite cycles, pause/resume, controlled stop, and explicit simulated fault recovery.

Milestone 3 adds pure U16, I16, U32, and I32 register-word codecs with explicit byte and
word order, immutable documentary register metadata, and a conservative read-only
catalog. It performs no register or device I/O. The target drive's 32-bit layout and
runtime address convention remain explicitly unverified.

Milestone 4 composes that codec and catalog with a synchronous symbolic reader and an
in-memory fake transport. Explicit immutable allowlists separate operational telemetry
from disabled-by-default engineering inspection. One-shot snapshots preserve raw words,
fixture-only validity, ambiguity, and per-field failures. All records are synthetic;
no genuine raw drive captures are available or claimed.

Milestone 5 adds documentation only: a source-specific evidence matrix, separate offline,
raw-read, typed-telemetry and motion gates, and a future bounded read-only commissioning
design. Gate A (offline) passes; Gates B (real raw reads), C (trusted physical telemetry)
and D (motion) remain blocked. The exact installed identities and compatible communication
manual are missing. Series C0A.06 word-order options do not verify the installed layout.
No real transport or adapter skeleton was added, and no device or network was accessed.
Milestone 6 reviewed five immutable local PDF excerpts. Milestone 7 applies the manual's
generic FC03 parameter-read rule to three read-only U16 monitor parameters: `U41.0A`
servo status, `U41.08` planning group, and `U40.04` raw digital-input status. It adds a
Pi-only, explicitly armed, one-request diagnostic and a harmless configuration preview.
No serial discovery, numeric-address interface, retry, polling, write path, or GUI access
to RS485 exists. Historical successful LabVIEW operation supports the communication
method but is not a current Raspberry Pi capture or installed-wiring verification.

The selected future homing strategy is `POSITIVE_LIMIT_REFERENCE`: PL is both the
positive travel limit and initial reference, NL remains the independent negative limit,
and an independent HSW and encoder-index refinement are deferred. This behavior exists
only in deterministic simulation. The family manual documents drive-internal positive
limit homing mode 18, but installed drive/firmware applicability and configuration remain
unverified. Real Servo On, Fault Reset, homing, motion, and register writes remain
prohibited.

There is still no network client or server, deployed Raspberry Pi service, monitoring
service, camera or temperature implementation, deployment unit, or executable real
hardware-control path. The GUI remains in-process simulation-only and cannot reach the
diagnostic transport.

## Responsibilities

- **Windows:** runs only the PySide6 GUI. It sends validated high-level requests to the Pi
  API and never opens RS485 or reads or writes servo registers directly.
- **Raspberry Pi motion service:** will be the sole owner of USB-to-RS485 and the only
  process allowed to communicate with the STEPPERONLINE A6-RS drive.
- **Raspberry Pi monitoring service:** will handle camera, video, recording, files,
  DS18B20 temperature, and Pi health independently from motion control.
- **A6-RS drive:** performs the servo loop, encoder processing, position trajectories,
  acceleration/deceleration, and drive-internal homing.
- **Independent hardware safety system:** removes motion-producing capability through the
  physical E-stop, STO or Servo Enable path, and PL/NL travel limits without depending on
  Windows, the Pi, software, networking, or RS485.

PLC, LabVIEW, VISA, ActiveX, and MX Component are not part of the new architecture.

## Development environment

Python 3.12 or later is required. Create and populate a project virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

Local configuration will use `config/common.local.toml`, `config/pi.local.toml`, and
`config/windows.local.toml`. Copy the corresponding example files and keep local values
out of version control. The examples deliberately leave hardware addresses and calibrated
motion limits unconfigured.

## Launch the in-process simulation GUI

Install the application and development dependencies into the project virtual environment
as shown above, then run:

```powershell
.\.venv\Scripts\python -m knee_rig.gui.app
```

The window is visibly labelled `SIMULATION`. Startup never connects, acquires a lease,
enables the simulated servo, homes, moves, or resumes. Motion uses uncalibrated application
units only; no joint-angle conversion is offered.

## Run the simulation and GUI tests

Qt smoke tests set `QT_QPA_PLATFORM=offscreen`, so the default suite does not require a
physical display:

```powershell
.\.venv\Scripts\ruff check .
.\.venv\Scripts\ruff format --check .
.\.venv\Scripts\mypy src
.\.venv\Scripts\pytest -q
```

The default pytest configuration excludes `tests/hardware/`. Do not run hardware-marked
tests without explicit authorization. Until safety hardware, model/firmware, register
encoding, direction, limits, and calibration are verified, real Servo On, homing,
automatic cycling, absolute-position motion, and persistent parameter writes are
prohibited.

## Prepare a one-shot laboratory read

On the Raspberry Pi, create an untracked local configuration with the exact stable
`/dev/serial/by-id/...` path. Preview the request without opening the device:

```bash
python -m knee_rig.motion.diagnostics validate-config \
  --config config/pi.local.toml --register SERVO_STATUS
```

Only after Stop Points A and B in the commissioning checklist and explicit authorization
for that exact read, run one armed request:

```bash
python -m knee_rig.motion.diagnostics read \
  --config config/pi.local.toml --register SERVO_STATUS \
  --arm-read-only-hardware
```

Each invocation permits one allowlisted FC03/U16 request and closes the port afterward.

The pure codec and catalog tests can be run independently:

```powershell
.\.venv\Scripts\python -m pytest -q tests/unit/test_register_codec.py `
  tests/unit/test_register_spec.py tests/unit/test_register_catalog.py
```

## Repository layout

Run the offline read-boundary tests with the existing project environment:

```powershell
.\.venv\Scripts\python -m pytest -q tests/unit/test_read_transport.py `
  tests/unit/test_read_only_reader.py tests/unit/test_read_boundary_safety.py `
  tests/integration/test_offline_read_snapshot.py
```

No port, device, real transport, or network service is needed by these tests.

```text
servo-rs485-pyside6/
├── config/                 Safe shared configuration examples
├── deploy/                 Future deployment design placeholders
├── docs/                   Architecture, API, safety, and commissioning design
├── src/knee_rig/
│   ├── common/             Typed configuration, state, command, and telemetry models
│   ├── gui/                Windows UI and future API client
│   ├── monitoring/         Isolated Pi monitoring service
│   └── motion/             Authorization, servo interface, coordinator, and simulation
└── tests/
    ├── unit/
    ├── integration/
    └── hardware/           Explicitly authorized tests only
```

## Documentation

- [Architecture](docs/architecture.md)
- [Requirements](docs/requirements.md)
- [Safety and commissioning](docs/safety.md)
- [Proposed API](docs/api.md)
- [Homing design](docs/homing.md)
- [Register map](docs/register-map.md)
- [Deployment design](docs/deployment.md)
- [Hardware inventory](docs/hardware-inventory.md)
- [Evidence matrix and source limitations](docs/evidence-matrix.md)
- [New evidence intake manifest](docs/evidence/intake-manifest.md)
- [Hardware readiness and evidence requests](docs/hardware-readiness.md)
- [Future read-only commissioning design](docs/read-only-commissioning.md)
- [Laboratory Session 1 checklist](docs/lab-commissioning-session-1.md)
- [Laboratory observation record](docs/lab-observation-record.md)
- [Positive-limit homing commissioning plan](docs/pl-homing-commissioning.md)
- [Future milestone prompts](docs/codex-prompts.md)

Files under `docs/reference/` are evidence only. Do not edit, rename, move, or execute
them.
