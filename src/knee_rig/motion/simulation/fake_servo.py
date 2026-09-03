"""Deterministic fake servo with explicit ticks and injectable failures."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from knee_rig.common.config.models import HomingConfig
from knee_rig.common.models import (
    AlarmInfo,
    ConnectionState,
    HomingPhase,
    HomingState,
    HomingStrategy,
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
    PL_NEVER_FOUND = "PL_NEVER_FOUND"
    PL_STUCK_ACTIVE = "PL_STUCK_ACTIVE"
    BACKOFF_TIMEOUT = "BACKOFF_TIMEOUT"
    CONTROLLED_STOP_UNCONFIRMED = "CONTROLLED_STOP_UNCONFIRMED"


@dataclass(slots=True)
class _HomingOperation:
    phase: HomingPhase
    phase_ticks: int
    total_ticks: int
    overall_timeout_ticks: int
    search_start_position: float
    pl_trigger_position: float
    pl_detection_position: float | None
    backoff_start_position: float | None
    offset_target_position: float | None
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
        homing_config: HomingConfig | None = None,
    ) -> None:
        if not minimum_position_units < maximum_position_units:
            raise ValueError("minimum_position_units must be below maximum_position_units")
        self._clock = clock if clock is not None else ManualClock()
        self._minimum_position_units = minimum_position_units
        self._maximum_position_units = maximum_position_units
        self._homing_config = homing_config or HomingConfig(
            search_speed_units_per_tick=1.0,
            backoff_speed_units_per_tick=1.0,
            search_distance_units=5.0,
            backoff_distance_units=2.0,
            home_offset_units=-2.0,
            search_timeout_ticks=8,
            backoff_timeout_ticks=4,
        )
        self._connection = ConnectionState.DISCONNECTED
        self._servo = ServoState.SERVO_DISABLED
        self._homing = HomingState.UNHOMED
        self._homing_phase = HomingPhase.IDLE
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
        self._homing_phase = HomingPhase.IDLE
        self._motion = MotionState.IDLE
        self._operation = None
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        return OperationReceipt(True, True)

    def disconnect(self) -> OperationReceipt:
        self._connection = ConnectionState.DISCONNECTED
        self._servo = ServoState.SERVO_DISABLED
        self._homing = HomingState.UNHOMED
        self._homing_phase = HomingPhase.IDLE
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
            homing_strategy=HomingStrategy.POSITIVE_LIMIT_REFERENCE,
            homing_phase=self._homing_phase,
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
        if self._limits.pl_active and self._limits.nl_active:
            return OperationReceipt(
                False, False, "INVALID_LIMIT_STATE", "PL and NL are contradictory."
            )
        if self._limits.pl_active:
            return OperationReceipt(
                False,
                False,
                "PL_ACTIVE_AT_START",
                "PL is already active and no recovery sequence is authorized.",
            )
        if not self._valid_homing_config():
            return OperationReceipt(
                False,
                False,
                "HOMING_CONFIG_INVALID",
                "Positive-limit homing parameters are missing or incorrectly signed.",
            )
        self._homing = HomingState.HOMING
        self._homing_phase = HomingPhase.SEARCHING_POSITIVE_LIMIT
        self._motion = MotionState.STARTING
        trigger_distance = min(
            self._homing_config.search_distance_units / 2.0,
            self._homing_config.search_speed_units_per_tick * 2.0,
        )
        self._operation = _HomingOperation(
            phase=HomingPhase.SEARCHING_POSITIVE_LIMIT,
            phase_ticks=0,
            total_ticks=0,
            overall_timeout_ticks=timeout_ticks,
            search_start_position=self._position_units,
            pl_trigger_position=min(
                self._maximum_position_units,
                self._position_units + trigger_distance,
            ),
            pl_detection_position=None,
            backoff_start_position=None,
            offset_target_position=None,
            failure=self._next_homing_failure,
        )
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
        self._homing_phase = HomingPhase.IDLE
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
        operation = self._operation
        if isinstance(operation, _HomingOperation):
            if nl_active:
                self._enter_fault(
                    "UNEXPECTED_NL_DURING_HOMING",
                    "NL activated during positive-limit homing.",
                    motion_fault=True,
                )
                return
            if pl_active and operation.phase is HomingPhase.SEARCHING_POSITIVE_LIMIT:
                operation.pl_detection_position = self._position_units
                self._set_homing_phase(operation, HomingPhase.CONTROLLED_STOP_AT_LIMIT)
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
        self._homing_phase = HomingPhase.FAULT
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
        operation.total_ticks += 1
        operation.phase_ticks += 1
        if operation.total_ticks >= operation.overall_timeout_ticks:
            self._enter_homing_fault("HOMING_TIMEOUT", "Simulated homing timed out.")
            return
        if operation.phase is HomingPhase.SEARCHING_POSITIVE_LIMIT:
            self._motion = MotionState.MOVING
            if operation.phase_ticks >= self._homing_config.search_timeout_ticks:
                self._enter_homing_fault("HOMING_SEARCH_TIMEOUT", "PL search timed out.")
                return
            if operation.failure is HomingFailure.TIMEOUT:
                self._velocity_units_per_s = 0.0
                return
            step = self._homing_config.search_speed_units_per_tick
            self._position_units += step
            self._velocity_units_per_s = step
            travelled = self._position_units - operation.search_start_position
            never_found = operation.failure is HomingFailure.PL_NEVER_FOUND
            if never_found and travelled >= self._homing_config.search_distance_units:
                self._enter_homing_fault("PL_NOT_FOUND", "PL was not found within search distance.")
                return
            if not never_found and self._position_units >= operation.pl_trigger_position:
                self._limits = LimitInputState(True, False, False)
                operation.pl_detection_position = self._position_units
                self._set_homing_phase(operation, HomingPhase.CONTROLLED_STOP_AT_LIMIT)
            return
        if operation.phase is HomingPhase.CONTROLLED_STOP_AT_LIMIT:
            if operation.failure is HomingFailure.CONTROLLED_STOP_UNCONFIRMED:
                self._enter_homing_fault(
                    "HOMING_CONTROLLED_STOP_UNCONFIRMED",
                    "Controlled stop at PL was not confirmed.",
                )
                return
            self._velocity_units_per_s = 0.0
            operation.backoff_start_position = self._position_units
            self._set_homing_phase(operation, HomingPhase.BACKING_OFF_POSITIVE_LIMIT)
            return
        if operation.phase is HomingPhase.BACKING_OFF_POSITIVE_LIMIT:
            if operation.phase_ticks >= self._homing_config.backoff_timeout_ticks:
                self._enter_homing_fault("HOMING_BACKOFF_TIMEOUT", "PL backoff timed out.")
                return
            step = -self._homing_config.backoff_speed_units_per_tick
            self._position_units += step
            self._velocity_units_per_s = step
            assert operation.backoff_start_position is not None
            backed_off = operation.backoff_start_position - self._position_units
            if operation.failure is HomingFailure.BACKOFF_TIMEOUT:
                return
            if operation.failure is not HomingFailure.PL_STUCK_ACTIVE and backed_off >= step * -1:
                self._limits = LimitInputState(False, False, False)
            if backed_off >= self._homing_config.backoff_distance_units:
                if self._limits.pl_active:
                    self._enter_homing_fault("PL_STUCK_ACTIVE", "PL did not clear during backoff.")
                    return
                operation.offset_target_position = (
                    self._position_units + self._homing_config.home_offset_units
                )
                self._set_homing_phase(operation, HomingPhase.APPLYING_HOME_OFFSET)
            return
        if operation.phase is HomingPhase.APPLYING_HOME_OFFSET:
            assert operation.offset_target_position is not None
            if self._homing_config.home_offset_units >= 0:
                self._enter_homing_fault(
                    "WRONG_HOME_OFFSET_DIRECTION",
                    "Home offset must move in the negative direction.",
                )
                return
            delta = operation.offset_target_position - self._position_units
            if delta < 0:
                step = -min(abs(delta), self._homing_config.backoff_speed_units_per_tick)
                self._position_units += step
                self._velocity_units_per_s = step
            if math.isclose(
                self._position_units,
                operation.offset_target_position,
                abs_tol=1e-12,
            ):
                self._velocity_units_per_s = 0.0
                self._set_homing_phase(operation, HomingPhase.VERIFYING_COMPLETION)
            return
        if operation.phase is HomingPhase.VERIFYING_COMPLETION:
            if self._limits.pl_active:
                self._enter_homing_fault("PL_ACTIVE_AT_COMPLETION", "PL remained active.")
                return
            self._homing = HomingState.HOMED
            self._homing_phase = HomingPhase.COMPLETE
            self._motion = MotionState.IDLE
            self._position_units = 0.0
            self._velocity_units_per_s = 0.0
            self._torque_percent = 0.0
            self._operation = None

    def _set_homing_phase(self, operation: _HomingOperation, phase: HomingPhase) -> None:
        operation.phase = phase
        operation.phase_ticks = 0
        self._homing_phase = phase

    def _enter_homing_fault(self, code: str, message: str) -> None:
        self._homing_phase = HomingPhase.FAULT
        self._enter_fault(code, message, motion_fault=True)

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

    def _valid_homing_config(self) -> bool:
        config = self._homing_config
        return (
            config.strategy is HomingStrategy.POSITIVE_LIMIT_REFERENCE
            and config.search_direction == 1
            and config.search_speed_units_per_tick > 0
            and config.backoff_speed_units_per_tick > 0
            and config.search_distance_units > 0
            and config.backoff_distance_units > 0
            and config.home_offset_units < 0
            and config.search_timeout_ticks > 0
            and config.backoff_timeout_ticks > 0
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
            self._homing_phase = HomingPhase.FAULT
        if motion_fault or self._motion is not MotionState.IDLE:
            self._motion = MotionState.MOTION_FAULT
        self._operation = None
        self._velocity_units_per_s = 0.0
        self._torque_percent = 0.0
        self._record_alarm(code, message)

    def _record_alarm(self, code: str, message: str) -> None:
        self._active_fault_code = code
        self._alarms.append(AlarmInfo(code, message, self._clock.wall_time))
