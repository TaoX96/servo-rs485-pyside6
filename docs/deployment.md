# Raspberry Pi deployment design

Deployment remains design-only through Milestone 2. The repository does not provide,
install, enable, or start any systemd unit.

## Planned services

### `knee-motion.service`

- Runs the motion API and is the exclusive owner of the USB-to-RS485 serial device.
- Starts in simulation unless deliberately configured otherwise.
- Every start or restart clears the control lease and prior task, leaves the servo
  disabled, marks the machine unhomed, and does not issue motion or persistent writes.
- Uses a machine-specific `/dev/serial/by-id/...` value from a local configuration file.
  The serial device must never be hard-coded as `/dev/ttyUSB0`.
- Has bounded startup, shutdown, I/O, and recovery behavior. Restart policy must not
  restore or resume a previous motion task.

### `knee-monitoring.service`

- Independently owns camera, video, recording, media files, DS18B20, and Pi-health work.
- Does not import or call the motion service's servo transport and has no access to the
  serial-device group or path.
- Failure or restart must not terminate, restart, enable, disable, or command the motion
  service.

### Optional watchdog

A future watchdog may report process health and request ordinary systemd process restart.
It must never issue Servo On, home, motion, resume, fault reset, persistent writes, or task
restoration. It is not a safety function and cannot replace the E-stop, STO/enable path,
or physical limits. Do not add it unless this narrow responsibility remains enforceable.

## Identity and permissions

Services should run as dedicated, non-root users with separate least-privilege groups.
Only the motion-service identity receives permission for the configured by-id serial
device. The monitoring identity receives only the camera, sensor, and media-directory
permissions it needs. Unit hardening and writable paths must preserve required device
access without granting cross-service control.

## Configuration and secrets

Shared defaults come from safe packaged examples. Machine-specific settings live outside
the source tree or in ignored local files with restrictive permissions. They include the
serial by-id path, bind/advertised addresses, authentication material, media paths, and
verified machine limits. Logs and configuration snapshots must redact secrets and lease
tokens.

Configuration loading must fail closed: missing hardware identity, unverified calibration,
or disabled feature gates keeps real enable, homing, and motion unavailable. Normal
service startup never writes persistent drive parameters.

## Startup ordering and failure handling

The motion and monitoring services do not depend on one another for process startup.
Device and network readiness may affect each service's own readiness but never causes
automatic motion. Network availability does not authorize control.

Motion-service failure leaves independent hardware safety responsible for risk reduction.
A systemd restart returns to disabled, unhomed, idle state and requires explicit operator
recovery. Monitoring failure is reported independently and does not change motion state.
Log rotation, media storage exhaustion, camera failure, or DS18B20 failure must not
propagate into the motion process.

## Logging

Use structured journald-compatible logs with timestamps, service/version identity, state
transitions, command IDs, lease events, alarms, communication faults, and recovery
confirmations. Keep motion safety events separate from high-volume monitoring/media
events. Set bounded retention and never log credentials, lease secrets, or image payloads.

## Future deployment gate

Before creating units, define the dedicated users/groups, udev permissions for the exact
adapter, configuration paths, API authentication and TLS/network policy, log retention,
shutdown semantics, health checks, and service hardening. Unit installation and startup
require a later explicitly approved milestone.
