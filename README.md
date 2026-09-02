# Knee Rig Control

This repository defines a distributed control and monitoring system for a knee-test rig.
The intended operator interface is a PySide6 application on Windows, while a Raspberry Pi
owns motion communication and monitoring services. The project is currently at
**Milestone 1: simulation-only foundation**.

Milestone 1 implements strict layered configuration, serializable state/API models,
central command authorization, a transport-free servo interface, a deterministic fake
servo, an in-process motion coordinator, and unit tests. It does not implement a network
server, GUI, monitoring service, real servo driver, or executable hardware-control path.

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

## Run the simulation tests

The simulation has no hardware, network, GUI, or real-time entry point. Exercise it
through the deterministic unit suite:

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

## Repository layout

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
- [Future milestone prompts](docs/codex-prompts.md)

Files under `docs/reference/` are evidence only. Do not edit, rename, move, or execute
them.
