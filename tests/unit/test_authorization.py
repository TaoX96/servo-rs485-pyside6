"""The single authorizer enforces all command and state gates."""

from __future__ import annotations

import unittest
from dataclasses import replace

from knee_rig.common.models import (
    CommandName,
    ConnectionState,
    ControlledStopPayload,
    CyclePayload,
    DisableServoPayload,
    EnableServoPayload,
    ErrorCode,
    HomePayload,
    HomingState,
    LimitInputState,
    MotionState,
    PausePayload,
    ResetFaultPayload,
    ResumePayload,
    ServiceState,
    ServoState,
    SingleMovePayload,
    StateSnapshot,
)
from knee_rig.motion.state_machine import AuthorizationContext, StateAuthorizer
from tests.unit.support import command, enabled_simulation_config


class AuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = StateAuthorizer()
        self.config = enabled_simulation_config()
        self.context = AuthorizationContext(True, 0.0)
        self.base = StateSnapshot(
            service=ServiceState.READY,
            connection=ConnectionState.CONNECTED,
            servo=ServoState.SERVO_DISABLED,
            homing=HomingState.UNHOMED,
            motion=MotionState.IDLE,
        )

    def test_every_allowlisted_command_has_a_valid_state(self) -> None:
        cases = [
            (
                command(CommandName.ENABLE_SERVO, EnableServoPayload(True)),
                self.base,
            ),
            (
                command(CommandName.DISABLE_SERVO, DisableServoPayload(True)),
                replace(self.base, servo=ServoState.SERVO_ENABLED),
            ),
            (
                command(CommandName.HOME, HomePayload(5)),
                replace(self.base, servo=ServoState.SERVO_ENABLED),
            ),
            (
                command(
                    CommandName.START_SINGLE_MOVE,
                    SingleMovePayload(position_units=5.0, speed_units_per_tick=1.0),
                ),
                replace(
                    self.base,
                    servo=ServoState.SERVO_ENABLED,
                    homing=HomingState.HOMED,
                ),
            ),
            (
                command(CommandName.START_CYCLE, CyclePayload(5.0, -5.0, 1.0, 2)),
                replace(
                    self.base,
                    servo=ServoState.SERVO_ENABLED,
                    homing=HomingState.HOMED,
                ),
            ),
            (
                command(CommandName.PAUSE, PausePayload()),
                replace(
                    self.base,
                    servo=ServoState.SERVO_ENABLED,
                    homing=HomingState.HOMED,
                    motion=MotionState.MOVING,
                ),
            ),
            (
                command(CommandName.RESUME, ResumePayload(True)),
                replace(
                    self.base,
                    servo=ServoState.SERVO_ENABLED,
                    homing=HomingState.HOMED,
                    motion=MotionState.PAUSED,
                ),
            ),
            (
                command(CommandName.CONTROLLED_STOP, ControlledStopPayload()),
                replace(
                    self.base,
                    servo=ServoState.SERVO_ENABLED,
                    homing=HomingState.HOMED,
                    motion=MotionState.MOVING,
                ),
            ),
            (
                command(CommandName.RESET_FAULT, ResetFaultPayload(True)),
                replace(
                    self.base,
                    service=ServiceState.FAULT,
                    active_fault_code="TEST_FAULT",
                    recovery_required=True,
                ),
            ),
        ]
        for request, state in cases:
            with self.subTest(command=request.name):
                decision = self.authorizer.authorize(
                    request,
                    state,
                    self.config,
                    self.context,
                )
                self.assertTrue(decision.allowed, decision.failure)

    def test_every_command_rejects_without_a_lease(self) -> None:
        requests = [
            command(CommandName.ENABLE_SERVO, EnableServoPayload(True)),
            command(CommandName.DISABLE_SERVO, DisableServoPayload(True)),
            command(CommandName.HOME, HomePayload(5)),
            command(
                CommandName.START_SINGLE_MOVE,
                SingleMovePayload(position_units=1.0, speed_units_per_tick=1.0),
            ),
            command(CommandName.START_CYCLE, CyclePayload(1.0, -1.0, 1.0, 1)),
            command(CommandName.PAUSE, PausePayload()),
            command(CommandName.RESUME, ResumePayload(True)),
            command(CommandName.CONTROLLED_STOP, ControlledStopPayload()),
            command(CommandName.RESET_FAULT, ResetFaultPayload(True)),
        ]
        for request in requests:
            with self.subTest(command=request.name):
                decision = self.authorizer.authorize(
                    request,
                    self.base,
                    self.config,
                    AuthorizationContext(False, 0.0),
                )
                self.assertEqual(decision.failure.code, ErrorCode.LEASE_REQUIRED)

    def test_representative_invalid_states(self) -> None:
        cases = [
            (
                command(CommandName.HOME, HomePayload(5)),
                self.base,
                ErrorCode.SERVO_NOT_ENABLED,
            ),
            (
                command(CommandName.PAUSE, PausePayload()),
                self.base,
                ErrorCode.STATE_NOT_AUTHORIZED,
            ),
            (
                command(CommandName.RESUME, ResumePayload(True)),
                self.base,
                ErrorCode.STATE_NOT_AUTHORIZED,
            ),
            (
                command(CommandName.CONTROLLED_STOP, ControlledStopPayload()),
                self.base,
                ErrorCode.CONTROLLED_STOP_NOT_ALLOWED,
            ),
        ]
        for request, state, expected in cases:
            with self.subTest(command=request.name):
                decision = self.authorizer.authorize(
                    request,
                    state,
                    self.config,
                    self.context,
                )
                self.assertFalse(decision.allowed)
                self.assertEqual(decision.failure.code, expected)

    def test_unhomed_automatic_motion_is_rejected(self) -> None:
        request = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=5.0, speed_units_per_tick=1.0),
        )
        state = replace(self.base, servo=ServoState.SERVO_ENABLED)
        decision = self.authorizer.authorize(request, state, self.config, self.context)
        self.assertEqual(decision.failure.code, ErrorCode.HOMING_REQUIRED)

    def test_faulted_and_disconnected_states_are_rejected(self) -> None:
        request = command(CommandName.ENABLE_SERVO, EnableServoPayload(True))
        faulted = replace(
            self.base,
            service=ServiceState.FAULT,
            active_fault_code="TEST",
            recovery_required=True,
        )
        disconnected = replace(self.base, connection=ConnectionState.DISCONNECTED)
        self.assertEqual(
            self.authorizer.authorize(request, faulted, self.config, self.context).failure.code,
            ErrorCode.STATE_NOT_AUTHORIZED,
        )
        self.assertEqual(
            self.authorizer.authorize(
                request, disconnected, self.config, self.context
            ).failure.code,
            ErrorCode.NOT_CONNECTED,
        )

    def test_angle_motion_requires_valid_verified_calibration(self) -> None:
        request = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(joint_angle_deg=5.0, speed_units_per_tick=1.0),
        )
        state = replace(
            self.base,
            servo=ServoState.SERVO_ENABLED,
            homing=HomingState.HOMED,
        )
        unverified = enabled_simulation_config(calibration_verified=False)
        decision = self.authorizer.authorize(request, state, unverified, self.context)
        self.assertEqual(decision.failure.code, ErrorCode.CALIBRATION_NOT_VERIFIED)

    def test_new_motion_is_rejected_while_operation_is_active(self) -> None:
        request = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=5.0, speed_units_per_tick=1.0),
        )
        state = replace(
            self.base,
            servo=ServoState.SERVO_ENABLED,
            homing=HomingState.HOMED,
            motion=MotionState.MOVING,
        )
        decision = self.authorizer.authorize(request, state, self.config, self.context)
        self.assertEqual(decision.failure.code, ErrorCode.OPERATION_ACTIVE)

    def test_limits_reject_contradiction_and_motion_farther_in(self) -> None:
        request = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=5.0, speed_units_per_tick=1.0),
        )
        ready = replace(
            self.base,
            servo=ServoState.SERVO_ENABLED,
            homing=HomingState.HOMED,
        )
        contradictory = replace(ready, limits=LimitInputState(True, True, False))
        at_pl = replace(ready, limits=LimitInputState(True, False, False))
        self.assertEqual(
            self.authorizer.authorize(
                request, contradictory, self.config, self.context
            ).failure.code,
            ErrorCode.INVALID_LIMIT_STATE,
        )
        self.assertEqual(
            self.authorizer.authorize(request, at_pl, self.config, self.context).failure.code,
            ErrorCode.ACTIVE_LIMIT,
        )

    def test_motion_away_from_limit_requires_commissioning_policy(self) -> None:
        request = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=-5.0, speed_units_per_tick=1.0),
        )
        state = replace(
            self.base,
            servo=ServoState.SERVO_ENABLED,
            homing=HomingState.HOMED,
            limits=LimitInputState(True, False, False),
        )
        blocked = self.authorizer.authorize(request, state, self.config, self.context)
        allowed = self.authorizer.authorize(
            request,
            state,
            self.config,
            AuthorizationContext(True, 0.0, motion_away_from_limit_commissioned=True),
        )
        self.assertEqual(blocked.failure.code, ErrorCode.LIMIT_ESCAPE_NOT_COMMISSIONED)
        self.assertTrue(allowed.allowed)


if __name__ == "__main__":
    unittest.main()
