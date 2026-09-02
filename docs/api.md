# Proposed motion API

This document designs a future REST/JSON API rooted at `/v1`. Milestone 2 uses the same
framework-free command, state, telemetry, alarm, result, and error models through an
in-process simulation client. It does not implement or expose a network client or service.

## General rules

- The Raspberry Pi motion service is authoritative for validation and state.
- Only one controller may hold a control lease.
- Every state-changing request requires the lease token and a caller-generated UUID
  `command_id`.
- Commands are allowlisted high-level operations. No endpoint accepts an arbitrary Modbus
  register address, function, width, or value.
- Request acceptance means only that validation and authorization succeeded. Completion is
  a separate status based on confirmed drive feedback.
- JSON fields use explicit units, such as `joint_angle_deg`, `motor_speed_rpm`,
  `acceleration_time_ms`, and `wait_time_ms`.
- Authentication and transport security remain deployment gates and must be defined before
  binding the service beyond a controlled network.

## Control lease

| Method and path | Purpose |
|---|---|
| `POST /v1/control-lease` | Acquire the lease when no controller owns it. |
| `POST /v1/control-lease/renew` | Renew the active lease before its bounded expiry. |
| `DELETE /v1/control-lease` | Release the caller's lease. |

Acquisition returns an opaque lease token, lease ID, issue timestamp, and expiry timestamp.
The token is sent in an authorization header and must not appear in logs or telemetry.
Lease acquisition never enables, homes, moves, resumes, resets a fault, or changes drive
parameters.

On lease expiry while idle, the service rejects new state-changing requests until a new
lease is acquired. On expiry during motion, it requests a controlled stop when
communication permits, rejects further motion, enters `FAULT`, and requires explicit
operator recovery. It does not automatically issue Servo Off. Lease or network behavior is
not a hardware E-stop.

## Command endpoint

`POST /v1/commands/{operation}` accepts:

```json
{
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "parameters": {},
  "operator_confirmation": true
}
```

The lease token is carried separately. A repeated command ID with the identical operation
and canonical payload returns the original recorded acknowledgement or outcome without
executing it again. Reuse with a different operation or payload returns HTTP `409` with
`COMMAND_ID_CONFLICT`.

An accepted response contains the command ID, operation, acceptance time, current state,
and `ACCEPTED`, `RUNNING`, `SUCCEEDED`, `REJECTED`, `CANCELLED`, or `FAILED`
status. Long-running command status is available at
`GET /v1/commands/{command_id}`.

## Allowlisted operator operations

| Operation | Required state and validation | Completion |
|---|---|---|
| `enable_servo` | Service available, servo disabled, motion idle, feature enabled, explicit confirmation, and commissioned safety gates satisfied. | Confirmed enabled feedback without motion. |
| `disable_servo` | Service available and motion idle; moving systems require controlled stop first. | Confirmed disabled feedback. |
| `home` | Servo enabled, unhomed, idle, homing allowed, bounded parameters, and verified safety/homing configuration. | All homing completion conditions are satisfied. |
| `start_single_move` | Servo enabled, homed, idle, motion allowed, calibration verified, and target/rate values within configured limits. | Confirmed terminal state and expected position. |
| `start_cycle` | Same gates as a single move plus a positive bounded cycle count and validated waits. | Requested finite count confirmed by software-side completed-cycle tracking. |
| `pause` | Motion running and drive behavior for pause has been verified. | Confirmed paused/non-advancing state. |
| `resume` | Motion paused, same lease active, no fault, authorization still valid, and explicit confirmation. | Confirmed running state. |
| `controlled_stop` | Motion running, paused, or already stopping. Repeats are idempotent. | Confirmed nonmoving state or a fault outcome. |
| `reset_fault` | Fault present, motion blocked, explicit operator confirmation, and reset allowed for the alarm. | Fault reset confirmed; never enables, homes, starts, or resumes motion. |

Commands outside their authorized state return a rejection without drive I/O. Automatic
cycling and absolute-position motion always require `HOMED`. Bounds apply to angle,
position units, speed, acceleration, deceleration, wait time, torque, temperature, and
cycle count as relevant. Zero or missing angle calibration rejects angle-based commands.

## Read-only endpoints

| Method and path | Semantics |
|---|---|
| `GET /v1/health` | Service liveness/readiness, version, simulation flag, and dependency health; never changes state. |
| `GET /v1/motion-state` | Current service, servo, homing, and motion states plus active command metadata. |
| `GET /v1/telemetry` | Latest validated sample with source timestamp, receive timestamp, sequence number, age, validity, quality reason, and explicit units. |
| `GET /v1/alarms` | Active and retained alarm summaries with timestamps and acknowledged/reset state. |

Stale telemetry is explicitly marked invalid or stale; absence of fresh data must not be
represented as zero. Query endpoints do not require a control lease and cannot trigger
recovery.

## Error format

```json
{
  "error": {
    "code": "STATE_NOT_AUTHORIZED",
    "message": "Homing is required before absolute motion.",
    "command_id": "550e8400-e29b-41d4-a716-446655440000",
    "state": {
      "service": "READY",
      "connection": "CONNECTED",
      "servo": "SERVO_ENABLED",
      "homing": "UNHOMED",
      "motion": "IDLE"
    },
    "retryable": false,
    "details": {}
  }
}
```

Stable codes include malformed request, validation failure, lease required, lease
conflict, command-ID conflict, state not authorized, feature disabled, calibration not
verified, stale feedback, drive alarm, communication failure, and internal fault. Details
are bounded and contain no credentials or raw untrusted payloads.

## Engineering-only operations

Electronic gearing, DI assignments, homing configuration, calibration acceptance, and
other persistent or machine-defining changes are engineering-only. They are disabled by
default, isolated from normal operation, require Servo Off, a logged reason, explicit
authorization, configuration backup, and read-back verification. No engineering endpoint
is implemented through Milestone 2, and future engineering design must still not expose an
arbitrary register read/write API.
