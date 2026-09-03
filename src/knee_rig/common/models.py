"""Serializable framework-free state, command, telemetry, and error models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ServiceState(StrEnum):
    STARTING = "STARTING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


class ConnectionState(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    COMMUNICATION_FAULT = "COMMUNICATION_FAULT"


class ServoState(StrEnum):
    SERVO_DISABLED = "SERVO_DISABLED"
    SERVO_ENABLING = "SERVO_ENABLING"
    SERVO_ENABLED = "SERVO_ENABLED"
    SERVO_DISABLING = "SERVO_DISABLING"
    SERVO_FAULT = "SERVO_FAULT"


class HomingState(StrEnum):
    UNHOMED = "UNHOMED"
    HOMING = "HOMING"
    HOMED = "HOMED"
    HOMING_FAULT = "HOMING_FAULT"


class HomingStrategy(StrEnum):
    POSITIVE_LIMIT_REFERENCE = "POSITIVE_LIMIT_REFERENCE"


class HomingPhase(StrEnum):
    IDLE = "IDLE"
    SEARCHING_POSITIVE_LIMIT = "SEARCHING_POSITIVE_LIMIT"
    CONTROLLED_STOP_AT_LIMIT = "CONTROLLED_STOP_AT_LIMIT"
    BACKING_OFF_POSITIVE_LIMIT = "BACKING_OFF_POSITIVE_LIMIT"
    APPLYING_HOME_OFFSET = "APPLYING_HOME_OFFSET"
    VERIFYING_COMPLETION = "VERIFYING_COMPLETION"
    COMPLETE = "COMPLETE"
    FAULT = "FAULT"


class MotionState(StrEnum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    MOVING = "MOVING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    MOTION_FAULT = "MOTION_FAULT"


@dataclass(frozen=True, slots=True)
class LimitInputState:
    pl_active: bool = False
    nl_active: bool = False
    hsw_active: bool = False

    def to_dict(self) -> dict[str, bool]:
        return {
            "pl_active": self.pl_active,
            "nl_active": self.nl_active,
            "hsw_active": self.hsw_active,
        }


@dataclass(frozen=True, slots=True)
class ServoStatus:
    connection: ConnectionState = ConnectionState.DISCONNECTED
    servo: ServoState = ServoState.SERVO_DISABLED
    homing: HomingState = HomingState.UNHOMED
    motion: MotionState = MotionState.IDLE
    homing_strategy: HomingStrategy = HomingStrategy.POSITIVE_LIMIT_REFERENCE
    homing_phase: HomingPhase = HomingPhase.IDLE
    limits: LimitInputState = LimitInputState()
    active_fault_code: str | None = None


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    service: ServiceState
    connection: ConnectionState
    servo: ServoState
    homing: HomingState
    motion: MotionState
    homing_strategy: HomingStrategy = HomingStrategy.POSITIVE_LIMIT_REFERENCE
    homing_phase: HomingPhase = HomingPhase.IDLE
    limits: LimitInputState = LimitInputState()
    active_fault_code: str | None = None
    active_command_id: UUID | None = None
    recovery_required: bool = False

    @property
    def has_blocking_fault(self) -> bool:
        return (
            self.service is ServiceState.FAULT
            or self.connection is ConnectionState.COMMUNICATION_FAULT
            or self.servo is ServoState.SERVO_FAULT
            or self.homing is HomingState.HOMING_FAULT
            or self.motion is MotionState.MOTION_FAULT
            or self.active_fault_code is not None
            or self.recovery_required
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "service": self.service.value,
            "connection": self.connection.value,
            "servo": self.servo.value,
            "homing": self.homing.value,
            "homing_strategy": self.homing_strategy.value,
            "homing_phase": self.homing_phase.value,
            "motion": self.motion.value,
            "limits": self.limits.to_dict(),
            "active_fault_code": self.active_fault_code,
            "active_command_id": (
                str(self.active_command_id) if self.active_command_id is not None else None
            ),
            "recovery_required": self.recovery_required,
        }


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    sequence: int
    acquisition_time: datetime
    monotonic_s: float
    valid: bool
    fresh: bool
    position_units: float
    velocity_units_per_s: float
    torque_percent: float
    limits: LimitInputState
    quality_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "acquisition_time": self.acquisition_time.isoformat(),
            "monotonic_s": self.monotonic_s,
            "valid": self.valid,
            "fresh": self.fresh,
            "position_units": self.position_units,
            "velocity_units_per_s": self.velocity_units_per_s,
            "torque_percent": self.torque_percent,
            "limits": self.limits.to_dict(),
            "quality_reason": self.quality_reason,
            "units": {
                "position": "position_units",
                "velocity": "position_units_per_second",
                "torque": "percent",
                "monotonic": "seconds",
            },
        }


@dataclass(frozen=True, slots=True)
class AlarmInfo:
    code: str
    message: str
    occurred_at: datetime
    active: bool = True
    simulated: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "occurred_at": self.occurred_at.isoformat(),
            "active": self.active,
            "simulated": self.simulated,
        }


class CommandName(StrEnum):
    ENABLE_SERVO = "enable_servo"
    DISABLE_SERVO = "disable_servo"
    HOME = "home"
    START_SINGLE_MOVE = "start_single_move"
    START_CYCLE = "start_cycle"
    PAUSE = "pause"
    RESUME = "resume"
    CONTROLLED_STOP = "controlled_stop"
    RESET_FAULT = "reset_fault"


@dataclass(frozen=True, slots=True)
class EnableServoPayload:
    operator_confirmation: bool

    def to_dict(self) -> dict[str, object]:
        return {"operator_confirmation": self.operator_confirmation}


@dataclass(frozen=True, slots=True)
class DisableServoPayload:
    operator_confirmation: bool

    def to_dict(self) -> dict[str, object]:
        return {"operator_confirmation": self.operator_confirmation}


@dataclass(frozen=True, slots=True)
class HomePayload:
    timeout_ticks: int

    def to_dict(self) -> dict[str, object]:
        return {"timeout_ticks": self.timeout_ticks}


@dataclass(frozen=True, slots=True)
class SingleMovePayload:
    position_units: float | None = None
    joint_angle_deg: float | None = None
    speed_units_per_tick: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return {
            "position_units": self.position_units,
            "joint_angle_deg": self.joint_angle_deg,
            "speed_units_per_tick": self.speed_units_per_tick,
        }


@dataclass(frozen=True, slots=True)
class CyclePayload:
    positive_position_units: float
    negative_position_units: float
    speed_units_per_tick: float
    cycle_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "positive_position_units": self.positive_position_units,
            "negative_position_units": self.negative_position_units,
            "speed_units_per_tick": self.speed_units_per_tick,
            "cycle_count": self.cycle_count,
        }


@dataclass(frozen=True, slots=True)
class PausePayload:
    def to_dict(self) -> dict[str, object]:
        return {}


@dataclass(frozen=True, slots=True)
class ResumePayload:
    operator_confirmation: bool

    def to_dict(self) -> dict[str, object]:
        return {"operator_confirmation": self.operator_confirmation}


@dataclass(frozen=True, slots=True)
class ControlledStopPayload:
    def to_dict(self) -> dict[str, object]:
        return {}


@dataclass(frozen=True, slots=True)
class ResetFaultPayload:
    operator_confirmation: bool

    def to_dict(self) -> dict[str, object]:
        return {"operator_confirmation": self.operator_confirmation}


type CommandPayload = (
    EnableServoPayload
    | DisableServoPayload
    | HomePayload
    | SingleMovePayload
    | CyclePayload
    | PausePayload
    | ResumePayload
    | ControlledStopPayload
    | ResetFaultPayload
)

_PAYLOAD_TYPES: dict[CommandName, type[object]] = {
    CommandName.ENABLE_SERVO: EnableServoPayload,
    CommandName.DISABLE_SERVO: DisableServoPayload,
    CommandName.HOME: HomePayload,
    CommandName.START_SINGLE_MOVE: SingleMovePayload,
    CommandName.START_CYCLE: CyclePayload,
    CommandName.PAUSE: PausePayload,
    CommandName.RESUME: ResumePayload,
    CommandName.CONTROLLED_STOP: ControlledStopPayload,
    CommandName.RESET_FAULT: ResetFaultPayload,
}


@dataclass(frozen=True, slots=True)
class CommandEnvelope:
    command_id: UUID
    name: CommandName
    payload: CommandPayload

    def __post_init__(self) -> None:
        expected = _PAYLOAD_TYPES[self.name]
        if not isinstance(self.payload, expected):
            raise TypeError(f"{self.name.value} requires {expected.__name__}")

    @classmethod
    def from_values(
        cls,
        command_id: str,
        name: CommandName,
        payload: CommandPayload,
    ) -> CommandEnvelope:
        try:
            parsed = UUID(command_id)
        except (ValueError, AttributeError) as exc:
            raise ValueError("command_id must be a valid UUID") from exc
        return cls(parsed, name, payload)

    def to_dict(self) -> dict[str, object]:
        return {
            "command_id": str(self.command_id),
            "name": self.name.value,
            "payload": self.payload.to_dict(),
        }


class ErrorCode(StrEnum):
    VALIDATION_FAILED = "VALIDATION_FAILED"
    OPERATOR_CONFIRMATION_REQUIRED = "OPERATOR_CONFIRMATION_REQUIRED"
    LEASE_REQUIRED = "LEASE_REQUIRED"
    COMMAND_ID_CONFLICT = "COMMAND_ID_CONFLICT"
    STATE_NOT_AUTHORIZED = "STATE_NOT_AUTHORIZED"
    FEATURE_DISABLED = "FEATURE_DISABLED"
    NOT_CONNECTED = "NOT_CONNECTED"
    BLOCKING_FAULT = "BLOCKING_FAULT"
    OPERATION_ACTIVE = "OPERATION_ACTIVE"
    SERVO_NOT_ENABLED = "SERVO_NOT_ENABLED"
    HOMING_REQUIRED = "HOMING_REQUIRED"
    CALIBRATION_NOT_VERIFIED = "CALIBRATION_NOT_VERIFIED"
    INVALID_CALIBRATION = "INVALID_CALIBRATION"
    MOTION_LIMITS_UNCONFIGURED = "MOTION_LIMITS_UNCONFIGURED"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    INVALID_LIMIT_STATE = "INVALID_LIMIT_STATE"
    ACTIVE_LIMIT = "ACTIVE_LIMIT"
    LIMIT_ESCAPE_NOT_COMMISSIONED = "LIMIT_ESCAPE_NOT_COMMISSIONED"
    CONTROLLED_STOP_NOT_ALLOWED = "CONTROLLED_STOP_NOT_ALLOWED"
    COMMUNICATION_FAILURE = "COMMUNICATION_FAILURE"
    DRIVE_FAULT = "DRIVE_FAULT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


type DiagnosticValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    code: ErrorCode
    message: str
    details: dict[str, DiagnosticValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StateAuthorizationFailure:
    code: ErrorCode
    message: str
    retryable: bool = False
    details: dict[str, DiagnosticValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    failure: StateAuthorizationFailure | None = None


@dataclass(frozen=True, slots=True)
class CommandError:
    code: ErrorCode
    message: str
    command_id: UUID | None
    state: StateSnapshot
    retryable: bool
    details: dict[str, DiagnosticValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        bounded_details = dict(list(self.details.items())[:16])
        return {
            "code": self.code.value,
            "message": self.message,
            "command_id": str(self.command_id) if self.command_id is not None else None,
            "state": self.state.to_dict(),
            "retryable": self.retryable,
            "details": bounded_details,
        }


class CommandStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class CommandResult:
    command_id: UUID
    name: CommandName
    status: CommandStatus
    state: StateSnapshot
    error: CommandError | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "command_id": str(self.command_id),
            "name": self.name.value,
            "status": self.status.value,
            "state": self.state.to_dict(),
            "error": self.error.to_dict() if self.error is not None else None,
        }
