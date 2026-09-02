"""Deterministic fake servo with explicit ticks and injectable failures."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from knee_rig.common.models import (
    AlarmInfo,
    ConnectionState,
    HomingState,
    LimitInputState,
    MotionState,
    ServoState,
    ServoStatus,
    TelemetrySnapshot,
)
from knee_rig.motion.driver import OperationReceipt
from knee_rig.motion.simulation.clock import ManualClock


class HomingFailure(StrEnum):
    TIMEOUT = "TIMEOUT"
    HSW_NOT_FOUND = "HSW_NOT_FOUND"


@dataclass(slots=True)
class _HomingOperation:
    elapsed_ticks: int
    timeout_ticks: int
    failure: HomingFailure | None


@dataclass(slots=True)
class _MoveOperation:
    target_position_units: float
    speed_units_per_tick: float


@dataclass(slots=True)
class _CycleOperation:
    positive_position_units: float
    negative_position_units: float
    speed_units_per_tick: float
    requested_cycles: int
    target_position_units: float
    travelling_positive: bool


_Operation = _HomingOperation | _MoveOperation | _CycleOperation


class FakeServo:
    """A safe simulation: no sleeping, threads, device discovery, I/O, or calibration."""

    def __init__(
        self,
        *,
        clock: ManualClock | None = None,
        minimum_position_units: float = -100.0,
        maximum_position_units: float = 100.0,
    ) -> None:
        if not minimum_position_units < maximum_position_units:
            raise ValueError("minimum_position_units must be below maximum_position_units")
        self._clock = clock if clock is not None else ManualClock()
        self._minimum_position_units = minimum_position_units
        self._maximum_position_units = maximum_position_units
        self._connection = ConnectionState.DISCONNECTED
        self._servo = ServoState.SERVO_DISABLED
        self._homing = HomingState.UNHOMED
        self._motion = MotionState.IDLE
        self._limits = LimitInputState()
        self._active_fault_code: str | None = None
        self._alarms: list[AlarmInfo] = []
        self._operation: _Operation | None = None
        self._position_units = 0.0
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        self._sequence = 0
        self._completed_cycles = 0
        self._next_homing_failure: HomingFailure | None = None

    @property
    def completed_cycles(self) -> int:
        return self._completed_cycles

    @property
    def clock(self) -> ManualClock:
        return self._clock

    def connect(self) -> OperationReceipt:
        if self._connection is ConnectionState.CONNECTED:
            return OperationReceipt(True, True)
        self._connection = ConnectionState.CONNECTED
        self._servo = ServoState.SERVO_DISABLED
        self._homing = HomingState.UNHOMED
        self._motion = MotionState.IDLE
        self._operation = None
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        return OperationReceipt(True, True)

    def disconnect(self) -> OperationReceipt:
        self._connection = ConnectionState.DISCONNECTED
        self._servo = ServoState.SERVO_DISABLED
        self._homing = HomingState.UNHOMED
        self._motion = MotionState.IDLE
        self._operation = None
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        return OperationReceipt(True, True)

    def read_status(self) -> ServoStatus:
        return ServoStatus(
            connection=self._connection,
            servo=self._servo,
            homing=self._homing,
            motion=self._motion,
            limits=self._limits,
            active_fault_code=self._active_fault_code,
        )

    def request_servo_enable(self) -> OperationReceipt:
        rejected = self._reject_if_unavailable()
        if rejected is not None:
            return rejected
        if self._servo is not ServoState.SERVO_DISABLED or self._motion is not MotionState.IDLE:
            return OperationReceipt(
                False,
                False,
                "INVALID_STATE",
                "Servo is not disabled and idle.",
            )
        self._servo = ServoState.SERVO_ENABLED
        return OperationReceipt(True, True)

    def request_servo_disable(self) -> OperationReceipt:
        rejected = self._reject_if_unavailable()
        if rejected is not None:
            return rejected
        if self._motion is not MotionState.IDLE:
            return OperationReceipt(False, False, "OPERATION_ACTIVE", "Motion must be idle.")
        if self._servo is not ServoState.SERVO_ENABLED:
            return OperationReceipt(False, False, "INVALID_STATE", "Servo is not enabled.")
        self._servo = ServoState.SERVO_DISABLED
        return OperationReceipt(True, True)

    def request_homing(self, *, timeout_ticks: int) -> OperationReceipt:
        rejected = self._reject_if_unavailable()
        if rejected is not None:
            return rejected
        if self._servo is not ServoState.SERVO_ENABLED or self._motion is not MotionState.IDLE:
            return OperationReceipt(False, False, "INVALID_STATE", "Homing requires enabled idle.")
        if timeout_ticks <= 0:
            return OperationReceipt(False, False, "INVALID_ARGUMENT", "Timeout must be positive.")
        self._homing = HomingState.HOMING
        self._limits = LimitInputState(
            pl_active=self._limits.pl_active,
            nl_active=self._limits.nl_active,
            hsw_active=False,
        )
        self._operation = _HomingOperation(0, timeout_ticks, self._next_homing_failure)
        self._next_homing_failure = None
        return OperationReceipt(True, False)

    def start_single_move(
        self,
        *,
        position_units: float,
        speed_units_per_tick: float,
    ) -> OperationReceipt:
        rejected = self._reject_if_unavailable()
        if rejected is not None:
            return rejected
        if not self._motion_ready():
            return OperationReceipt(False, False, "INVALID_STATE", "Motion is not authorized.")
        if not self._valid_move_values(position_units, speed_units_per_tick):
            return OperationReceipt(False, False, "INVALID_ARGUMENT", "Move values are invalid.")
        self._motion = MotionState.STARTING
        self._operation = _MoveOperation(position_units, speed_units_per_tick)
        return OperationReceipt(True, False)

    def start_cycle(
        self,
        *,
        positive_position_units: float,
        negative_position_units: float,
        speed_units_per_tick: float,
        cycle_count: int,
    ) -> OperationReceipt:
        rejected = self._reject_if_unavailable()
        if rejected is not None:
            return rejected
        if not self._motion_ready():
            return OperationReceipt(False, False, "INVALID_STATE", "Motion is not authorized.")
        if (
            not self._valid_move_values(positive_position_units, speed_units_per_tick)
            or not self._valid_move_values(negative_position_units, speed_units_per_tick)
            or positive_position_units <= negative_position_units
            or cycle_count <= 0
        ):
            return OperationReceipt(False, False, "INVALID_ARGUMENT", "Cycle values are invalid.")
        self._completed_cycles = 0
        self._motion = MotionState.STARTING
        self._operation = _CycleOperation(
            positive_position_units=positive_position_units,
            negative_position_units=negative_position_units,
            speed_units_per_tick=speed_units_per_tick,
            requested_cycles=cycle_count,
            target_position_units=positive_position_units,
            travelling_positive=True,
        )
        return OperationReceipt(True, False)

    def pause(self) -> OperationReceipt:
        if self._motion is not MotionState.MOVING:
            return OperationReceipt(False, False, "INVALID_STATE", "Motion is not moving.")
        self._motion = MotionState.PAUSED
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        return OperationReceipt(True, True)

    def resume(self) -> OperationReceipt:
        rejected = self._reject_if_unavailable()
        if rejected is not None:
            return rejected
        if self._motion is not MotionState.PAUSED or self._operation is None:
            return OperationReceipt(False, False, "INVALID_STATE", "Motion is not paused.")
        self._motion = MotionState.MOVING
        return OperationReceipt(True, True)

    def request_controlled_stop(self) -> OperationReceipt:
        if self._connection is not ConnectionState.CONNECTED:
            return OperationReceipt(
                False,
                False,
                "COMMUNICATION_FAILURE",
                "Controlled stop could not be requested.",
            )
        if self._motion not in {
            MotionState.STARTING,
            MotionState.MOVING,
            MotionState.PAUSED,
            MotionState.STOPPING,
        }:
            return OperationReceipt(False, False, "INVALID_STATE", "No motion is active.")
        self._motion = MotionState.STOPPING
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        return OperationReceipt(True, False)

    def reset_fault(self) -> OperationReceipt:
        if self._connection is not ConnectionState.CONNECTED:
            return OperationReceipt(False, False, "NOT_CONNECTED", "Communication is unavailable.")
        if self._active_fault_code is None:
            return OperationReceipt(False, False, "NO_FAULT", "No fault is active.")
        self._active_fault_code = None
        self._alarms.clear()
        if self._servo is ServoState.SERVO_FAULT:
            self._servo = ServoState.SERVO_DISABLED
        if self._homing is HomingState.HOMING_FAULT:
            self._homing = HomingState.UNHOMED
        if self._motion is MotionState.MOTION_FAULT:
            self._motion = MotionState.IDLE
        self._operation = None
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        return OperationReceipt(True, True)

    def read_telemetry(self) -> TelemetrySnapshot:
        valid = self._connection is ConnectionState.CONNECTED
        return TelemetrySnapshot(
            sequence=self._sequence,
            acquisition_time=self._clock.wall_time,
            monotonic_s=self._clock.monotonic_s,
            valid=valid,
            fresh=valid,
            position_units=self._position_units,
            velocity_units_per_s=self._velocity_units_per_s,
            torque_percent=self._torque_percent,
            limits=self._limits,
            quality_reason=None if valid else "communication_unavailable",
        )

    def read_alarms(self) -> tuple[AlarmInfo, ...]:
        return tuple(self._alarms)

    def advance(self, ticks: int = 1) -> None:
        """Advance simulation deterministically; never sleep or use wall-clock time."""
        if ticks < 0:
            raise ValueError("ticks must not be negative")
        for _ in range(ticks):
            self._clock.advance(1.0)
            self._sequence += 1
            if self._motion is MotionState.STOPPING:
                self._operation = None
                self._motion = MotionState.IDLE
                self._velocity_units_per_s = 0.0
                self._torque_percent = 0.0
                continue
            if self._motion is MotionState.PAUSED:
                continue
            if self._connection is not ConnectionState.CONNECTED:
                continue
            operation = self._operation
            if isinstance(operation, _HomingOperation):
                self._advance_homing(operation)
            elif isinstance(operation, (_MoveOperation, _CycleOperation)):
                self._advance_motion(operation)

    def set_next_homing_failure(self, failure: HomingFailure | None) -> None:
        self._next_homing_failure = failure

    def set_limits(self, *, pl_active: bool, nl_active: bool, hsw_active: bool) -> None:
        self._limits = LimitInputState(pl_active, nl_active, hsw_active)
        if pl_active and nl_active:
            self._enter_fault(
                "LIMIT_STATE_CONTRADICTION",
                "PL and NL are simultaneously active.",
                motion_fault=self._motion is not MotionState.IDLE,
            )
            return
        direction = self._motion_direction()
        if (pl_active and direction > 0) or (nl_active and direction < 0):
            self._enter_fault(
                "LIMIT_ACTIVATED_DURING_MOTION",
                "A travel limit activated in the direction of motion.",
                motion_fault=True,
            )

    def inject_drive_fault(self, code: str = "SIMULATED_DRIVE_FAULT") -> None:
        self._enter_fault(
            code,
            "A deterministic simulated drive fault was injected.",
            servo_fault=True,
        )

    def inject_communication_fault(self) -> None:
        was_active = self._motion is not MotionState.IDLE or self._homing is HomingState.HOMING
        self._connection = ConnectionState.COMMUNICATION_FAULT
        self._homing = HomingState.UNHOMED
        self._operation = None
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        if was_active:
            self._motion = MotionState.MOTION_FAULT
        self._record_alarm(
            "SIMULATED_COMMUNICATION_FAULT",
            "Simulated communication was lost; motion authorization is invalid.",
        )

    def reconnect_after_communication_fault(self) -> OperationReceipt:
        if self._connection is not ConnectionState.COMMUNICATION_FAULT:
            return OperationReceipt(False, False, "INVALID_STATE", "No communication fault exists.")
        self._connection = ConnectionState.CONNECTED
        return OperationReceipt(True, True)

    def record_recovery_required_fault(self, code: str, message: str) -> None:
        self._active_fault_code = code
        self._record_alarm(code, message)

    def _advance_homing(self, operation: _HomingOperation) -> None:
        operation.elapsed_ticks += 1
        if operation.failure is HomingFailure.HSW_NOT_FOUND and operation.elapsed_ticks >= 3:
            self._homing = HomingState.HOMING_FAULT
            self._operation = None
            self._record_alarm("HSW_NOT_FOUND", "Simulated HSW was not found.")
            return
        if operation.elapsed_ticks >= operation.timeout_ticks:
            self._homing = HomingState.HOMING_FAULT
            self._operation = None
            self._record_alarm("HOMING_TIMEOUT", "Simulated homing timed out.")
            return
        if operation.failure is None and operation.elapsed_ticks >= 3:
            self._homing = HomingState.HOMED
            self._position_units = 0.0
            self._limits = LimitInputState(
                pl_active=self._limits.pl_active,
                nl_active=self._limits.nl_active,
                hsw_active=True,
            )
            self._operation = None

    def _advance_motion(self, operation: _MoveOperation | _CycleOperation) -> None:
        if self._motion is MotionState.STARTING:
            self._motion = MotionState.MOVING
        target = operation.target_position_units
        speed = operation.speed_units_per_tick
        delta = target - self._position_units
        if math.isclose(delta, 0.0, abs_tol=1e-12):
            self._complete_leg(operation)
            return
        direction = 1.0 if delta > 0 else -1.0
        if (direction > 0 and self._limits.pl_active) or (direction < 0 and self._limits.nl_active):
            self._enter_fault(
                "LIMIT_ACTIVATED_DURING_MOTION",
                "Motion attempted farther into an active limit.",
                motion_fault=True,
            )
            return
        step = min(abs(delta), speed) * direction
        self._position_units += step
        self._velocity_units_per_s = step
        self._torque_percent = min(25.0, abs(step) * 2.0)
        self._limits = LimitInputState(
            pl_active=self._position_units >= self._maximum_position_units,
            nl_active=self._position_units <= self._minimum_position_units,
            hsw_active=math.isclose(self._position_units, 0.0, abs_tol=1e-12),
        )
        if math.isclose(self._position_units, target, abs_tol=1e-12):
            self._complete_leg(operation)

    def _complete_leg(self, operation: _MoveOperation | _CycleOperation) -> None:
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        if isinstance(operation, _MoveOperation):
            self._operation = None
            self._motion = MotionState.IDLE
            return
        if operation.travelling_positive:
            operation.travelling_positive = False
            operation.target_position_units = operation.negative_position_units
            return
        self._completed_cycles += 1
        if self._completed_cycles >= operation.requested_cycles:
            self._operation = None
            self._motion = MotionState.IDLE
        else:
            operation.travelling_positive = True
            operation.target_position_units = operation.positive_position_units

    def _motion_ready(self) -> bool:
        return (
            self._connection is ConnectionState.CONNECTED
            and self._servo is ServoState.SERVO_ENABLED
            and self._homing is HomingState.HOMED
            and self._motion is MotionState.IDLE
            and self._active_fault_code is None
        )

    def _valid_move_values(self, target: float, speed: float) -> bool:
        return (
            math.isfinite(target)
            and math.isfinite(speed)
            and self._minimum_position_units <= target <= self._maximum_position_units
            and speed > 0
        )

    def _reject_if_unavailable(self) -> OperationReceipt | None:
        if self._connection is not ConnectionState.CONNECTED:
            return OperationReceipt(False, False, "NOT_CONNECTED", "Communication is unavailable.")
        if self._active_fault_code is not None:
            return OperationReceipt(False, False, "FAULT_ACTIVE", "Explicit recovery is required.")
        return None

    def _motion_direction(self) -> int:
        operation = self._operation
        if not isinstance(operation, (_MoveOperation, _CycleOperation)):
            return 0
        if operation.target_position_units > self._position_units:
            return 1
        if operation.target_position_units < self._position_units:
            return -1
        return 0

    def _enter_fault(
        self,
        code: str,
        message: str,
        *,
        servo_fault: bool = False,
        motion_fault: bool = False,
    ) -> None:
        self._active_fault_code = code
        if servo_fault:
            self._servo = ServoState.SERVO_FAULT
        if self._homing is HomingState.HOMING:
            self._homing = HomingState.HOMING_FAULT
        if motion_fault or self._motion is not MotionState.IDLE:
            self._motion = MotionState.MOTION_FAULT
        self._operation = None
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        self._record_alarm(code, message)

    def _record_alarm(self, code: str, message: str) -> None:
        self._active_fault_code = code
        self._alarms.append(AlarmInfo(code, message, self._clock.wall_time))
