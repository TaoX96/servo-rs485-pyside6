"""One auditable authorization layer for all allowlisted motion commands."""

from __future__ import annotations

import math
from dataclasses import dataclass

from knee_rig.common.config import AppConfig
from knee_rig.common.models import (
    AuthorizationDecision,
    CommandEnvelope,
    CommandName,
    ConnectionState,
    ControlledStopPayload,
    CyclePayload,
    DisableServoPayload,
    EnableServoPayload,
    ErrorCode,
    HomePayload,
    HomingState,
    HomingStrategy,
    MotionState,
    ResetFaultPayload,
    ResumePayload,
    ServiceState,
    ServoState,
    SingleMovePayload,
    StateAuthorizationFailure,
    StateSnapshot,
)


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    control_lease_active: bool
    current_position_units: float
    motion_away_from_limit_commissioned: bool = False


class StateAuthorizer:
    """Evaluate every safety and state gate without causing side effects."""

    def authorize(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        if not context.control_lease_active:
            return self._reject(ErrorCode.LEASE_REQUIRED, "An active control lease is required.")
        if state.limits.pl_active and state.limits.nl_active:
            return self._reject(
                ErrorCode.INVALID_LIMIT_STATE,
                "PL and NL cannot both be active.",
            )
        if command.name is CommandName.RESET_FAULT:
            return self._authorize_reset(command, state)
        if state.service is not ServiceState.READY:
            return self._reject(
                ErrorCode.STATE_NOT_AUTHORIZED,
                "The motion service is not ready.",
                service=state.service.value,
            )
        if state.connection is not ConnectionState.CONNECTED:
            return self._reject(ErrorCode.NOT_CONNECTED, "The simulated servo is not connected.")
        if state.has_blocking_fault:
            return self._reject(ErrorCode.BLOCKING_FAULT, "Explicit fault recovery is required.")

        handlers = {
            CommandName.ENABLE_SERVO: self._authorize_enable,
            CommandName.DISABLE_SERVO: self._authorize_disable,
            CommandName.HOME: self._authorize_home,
            CommandName.START_SINGLE_MOVE: self._authorize_single_move,
            CommandName.START_CYCLE: self._authorize_cycle,
            CommandName.PAUSE: self._authorize_pause,
            CommandName.RESUME: self._authorize_resume,
            CommandName.CONTROLLED_STOP: self._authorize_controlled_stop,
        }
        handler = handlers[command.name]
        return handler(command, state, config, context)

    def _authorize_enable(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        del context
        payload = command.payload
        assert isinstance(payload, EnableServoPayload)
        if not config.features.simulation or not config.features.allow_servo_enable:
            return self._reject(ErrorCode.FEATURE_DISABLED, "Simulated servo enable is disabled.")
        if not payload.operator_confirmation:
            return self._reject(
                ErrorCode.OPERATOR_CONFIRMATION_REQUIRED,
                "Servo enable requires explicit confirmation.",
            )
        if state.servo is not ServoState.SERVO_DISABLED or state.motion is not MotionState.IDLE:
            return self._reject(
                ErrorCode.STATE_NOT_AUTHORIZED,
                "Servo enable requires disabled, idle state.",
            )
        return AuthorizationDecision(True)

    def _authorize_disable(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        del config, context
        payload = command.payload
        assert isinstance(payload, DisableServoPayload)
        if not payload.operator_confirmation:
            return self._reject(
                ErrorCode.OPERATOR_CONFIRMATION_REQUIRED,
                "Servo disable requires explicit confirmation.",
            )
        if state.motion is not MotionState.IDLE:
            return self._reject(
                ErrorCode.OPERATION_ACTIVE,
                "Controlled stop and confirmed idle are required before Servo Off.",
            )
        if state.servo is not ServoState.SERVO_ENABLED:
            return self._reject(
                ErrorCode.STATE_NOT_AUTHORIZED,
                "The simulated servo is not enabled.",
            )
        return AuthorizationDecision(True)

    def _authorize_home(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        del context
        payload = command.payload
        assert isinstance(payload, HomePayload)
        if not config.features.simulation or not config.features.allow_homing:
            return self._reject(ErrorCode.FEATURE_DISABLED, "Simulated homing is disabled.")
        if state.servo is not ServoState.SERVO_ENABLED:
            return self._reject(ErrorCode.SERVO_NOT_ENABLED, "Servo must be enabled to home.")
        if state.motion is not MotionState.IDLE:
            return self._reject(ErrorCode.OPERATION_ACTIVE, "Motion is already active.")
        if state.homing is HomingState.HOMING:
            return self._reject(ErrorCode.OPERATION_ACTIVE, "Homing is already active.")
        if state.limits.pl_active:
            return self._reject(
                ErrorCode.ACTIVE_LIMIT,
                "PL is active at homing start and no recovery sequence is authorized.",
            )
        if payload.timeout_ticks <= 0:
            return self._reject(ErrorCode.VALIDATION_FAILED, "timeout_ticks must be positive.")
        homing = config.homing
        if (
            homing.strategy is not HomingStrategy.POSITIVE_LIMIT_REFERENCE
            or homing.search_direction != 1
            or homing.search_speed_units_per_tick <= 0
            or homing.backoff_speed_units_per_tick <= 0
            or homing.search_distance_units <= 0
            or homing.backoff_distance_units <= 0
            or homing.home_offset_units >= 0
            or homing.search_timeout_ticks <= 0
            or homing.backoff_timeout_ticks <= 0
        ):
            return self._reject(
                ErrorCode.VALIDATION_FAILED,
                "Positive-limit homing configuration is incomplete or incorrectly signed.",
            )
        return AuthorizationDecision(True)

    def _authorize_single_move(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        payload = command.payload
        assert isinstance(payload, SingleMovePayload)
        base = self._authorize_automatic_motion(state, config)
        if not base.allowed:
            return base
        has_units = payload.position_units is not None
        has_angle = payload.joint_angle_deg is not None
        if has_units == has_angle:
            return self._reject(
                ErrorCode.VALIDATION_FAILED,
                "Exactly one of position_units and joint_angle_deg is required.",
            )
        if not math.isfinite(payload.speed_units_per_tick) or payload.speed_units_per_tick <= 0:
            return self._reject(
                ErrorCode.VALIDATION_FAILED,
                "speed_units_per_tick must be finite and positive.",
            )
        if has_angle:
            calibration = config.calibration
            if not config.features.calibration_verified:
                return self._reject(
                    ErrorCode.CALIBRATION_NOT_VERIFIED,
                    "Angle motion requires verified calibration.",
                )
            if (
                calibration.position_units_per_joint_degree <= 0
                or calibration.direction_sign not in (-1, 1)
            ):
                return self._reject(
                    ErrorCode.INVALID_CALIBRATION,
                    "Angle calibration is missing, zero, or invalid.",
                )
            assert payload.joint_angle_deg is not None
            if not math.isfinite(payload.joint_angle_deg):
                return self._reject(ErrorCode.VALIDATION_FAILED, "joint_angle_deg must be finite.")
            limits = config.limits
            if limits.min_joint_angle_deg >= limits.max_joint_angle_deg:
                return self._reject(
                    ErrorCode.MOTION_LIMITS_UNCONFIGURED,
                    "Joint-angle limits are not configured.",
                )
            if not (
                limits.min_joint_angle_deg <= payload.joint_angle_deg <= limits.max_joint_angle_deg
            ):
                return self._reject(
                    ErrorCode.OUT_OF_RANGE,
                    "Requested joint angle is outside configured limits.",
                )
            target = calibration.position_units_for_angle(payload.joint_angle_deg)
        else:
            assert payload.position_units is not None
            if not math.isfinite(payload.position_units):
                return self._reject(ErrorCode.VALIDATION_FAILED, "position_units must be finite.")
            target = payload.position_units
        return self._authorize_limit_direction(target, state, context)

    def _authorize_cycle(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        payload = command.payload
        assert isinstance(payload, CyclePayload)
        base = self._authorize_automatic_motion(state, config)
        if not base.allowed:
            return base
        values = (
            payload.positive_position_units,
            payload.negative_position_units,
            payload.speed_units_per_tick,
        )
        if not all(math.isfinite(number) for number in values):
            return self._reject(ErrorCode.VALIDATION_FAILED, "Cycle values must be finite.")
        if payload.positive_position_units <= payload.negative_position_units:
            return self._reject(
                ErrorCode.VALIDATION_FAILED,
                "positive_position_units must exceed negative_position_units.",
            )
        if payload.speed_units_per_tick <= 0 or payload.cycle_count <= 0:
            return self._reject(
                ErrorCode.VALIDATION_FAILED,
                "Cycle speed and count must be positive.",
            )
        if config.limits.max_cycle_count <= 0:
            return self._reject(
                ErrorCode.MOTION_LIMITS_UNCONFIGURED,
                "Maximum cycle count is not configured.",
            )
        if payload.cycle_count > config.limits.max_cycle_count:
            return self._reject(ErrorCode.OUT_OF_RANGE, "Cycle count exceeds the configured limit.")
        for target in (payload.positive_position_units, payload.negative_position_units):
            decision = self._authorize_limit_direction(target, state, context)
            if not decision.allowed:
                return decision
        return AuthorizationDecision(True)

    def _authorize_pause(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        del command, config, context
        if state.motion is not MotionState.MOVING:
            return self._reject(
                ErrorCode.STATE_NOT_AUTHORIZED,
                "Pause is allowed only while moving.",
            )
        return AuthorizationDecision(True)

    def _authorize_resume(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        del config, context
        payload = command.payload
        assert isinstance(payload, ResumePayload)
        if state.motion is not MotionState.PAUSED:
            return self._reject(
                ErrorCode.STATE_NOT_AUTHORIZED,
                "Resume is allowed only from paused state.",
            )
        if not payload.operator_confirmation:
            return self._reject(
                ErrorCode.OPERATOR_CONFIRMATION_REQUIRED,
                "Resume requires explicit confirmation.",
            )
        return AuthorizationDecision(True)

    def _authorize_controlled_stop(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
        config: AppConfig,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        del config, context
        assert isinstance(command.payload, ControlledStopPayload)
        if state.motion not in {
            MotionState.STARTING,
            MotionState.MOVING,
            MotionState.PAUSED,
            MotionState.STOPPING,
        }:
            return self._reject(
                ErrorCode.CONTROLLED_STOP_NOT_ALLOWED,
                "Controlled stop requires active motion.",
            )
        return AuthorizationDecision(True)

    def _authorize_reset(
        self,
        command: CommandEnvelope,
        state: StateSnapshot,
    ) -> AuthorizationDecision:
        payload = command.payload
        assert isinstance(payload, ResetFaultPayload)
        if not payload.operator_confirmation:
            return self._reject(
                ErrorCode.OPERATOR_CONFIRMATION_REQUIRED,
                "Fault reset requires explicit confirmation.",
            )
        if state.connection is not ConnectionState.CONNECTED:
            return self._reject(
                ErrorCode.NOT_CONNECTED,
                "Communication must be restored before explicit fault reset.",
            )
        if not state.has_blocking_fault:
            return self._reject(
                ErrorCode.STATE_NOT_AUTHORIZED,
                "No blocking fault is present.",
            )
        if state.motion is MotionState.STOPPING:
            return self._reject(
                ErrorCode.OPERATION_ACTIVE,
                "Wait for controlled stop completion before fault reset.",
                retryable=True,
            )
        return AuthorizationDecision(True)

    def _authorize_automatic_motion(
        self,
        state: StateSnapshot,
        config: AppConfig,
    ) -> AuthorizationDecision:
        if not config.features.simulation or not config.features.allow_motion:
            return self._reject(ErrorCode.FEATURE_DISABLED, "Simulated motion is disabled.")
        if state.servo is not ServoState.SERVO_ENABLED:
            return self._reject(ErrorCode.SERVO_NOT_ENABLED, "Servo must be enabled.")
        if state.homing is not HomingState.HOMED:
            return self._reject(ErrorCode.HOMING_REQUIRED, "Successful homing is required.")
        if state.motion is not MotionState.IDLE:
            return self._reject(ErrorCode.OPERATION_ACTIVE, "Another motion operation is active.")
        return AuthorizationDecision(True)

    def _authorize_limit_direction(
        self,
        target_position_units: float,
        state: StateSnapshot,
        context: AuthorizationContext,
    ) -> AuthorizationDecision:
        moving_positive = target_position_units > context.current_position_units
        moving_negative = target_position_units < context.current_position_units
        if state.limits.pl_active and moving_positive:
            return self._reject(ErrorCode.ACTIVE_LIMIT, "Motion farther into PL is prohibited.")
        if state.limits.nl_active and moving_negative:
            return self._reject(ErrorCode.ACTIVE_LIMIT, "Motion farther into NL is prohibited.")
        moving_away = (state.limits.pl_active and moving_negative) or (
            state.limits.nl_active and moving_positive
        )
        if moving_away and not context.motion_away_from_limit_commissioned:
            return self._reject(
                ErrorCode.LIMIT_ESCAPE_NOT_COMMISSIONED,
                "Motion away from an active limit has not been commissioned.",
            )
        return AuthorizationDecision(True)

    @staticmethod
    def _reject(
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        **details: str | float | bool | None,
    ) -> AuthorizationDecision:
        return AuthorizationDecision(
            False,
            StateAuthorizationFailure(code, message, retryable, details),
        )
