"""Coordinator tests cover idempotency, serialization, restart, and lease faults."""

from __future__ import annotations

import json
import unittest
from uuid import uuid4

from knee_rig.common.models import (
    CommandEnvelope,
    CommandName,
    CommandStatus,
    ConnectionState,
    ControlledStopPayload,
    EnableServoPayload,
    ErrorCode,
    HomePayload,
    HomingState,
    MotionState,
    ResetFaultPayload,
    ServoState,
    SingleMovePayload,
)
from knee_rig.motion.service import MotionCoordinator
from knee_rig.motion.simulation import FakeServo
from tests.unit.support import command, enabled_simulation_config


class CoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.servo = FakeServo()
        self.coordinator = MotionCoordinator(enabled_simulation_config(), self.servo)
        self.coordinator.start()
        self.coordinator.connect()
        self.lease_id = uuid4()
        self.assertTrue(self.coordinator.acquire_control_lease(self.lease_id))

    def _enable_and_home(self) -> None:
        enable = command(CommandName.ENABLE_SERVO, EnableServoPayload(True))
        self.assertEqual(
            self.coordinator.handle(enable, lease_id=self.lease_id).status,
            CommandStatus.SUCCEEDED,
        )
        home = command(CommandName.HOME, HomePayload(5))
        self.assertEqual(
            self.coordinator.handle(home, lease_id=self.lease_id).status,
            CommandStatus.RUNNING,
        )
        self.servo.advance(3)
        self.coordinator.refresh()
        self.assertEqual(
            self.coordinator.result_for(home.command_id).status,
            CommandStatus.SUCCEEDED,
        )

    def test_uuid_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid UUID"):
            CommandEnvelope.from_values(
                "not-a-uuid",
                CommandName.ENABLE_SERVO,
                EnableServoPayload(True),
            )

    def test_same_id_and_payload_replays_recorded_result(self) -> None:
        request = command(CommandName.ENABLE_SERVO, EnableServoPayload(True))
        first = self.coordinator.handle(request, lease_id=self.lease_id)
        replay = self.coordinator.handle(request, lease_id=self.lease_id)
        self.assertIs(first, replay)
        self.assertEqual(self.coordinator.state.servo, ServoState.SERVO_ENABLED)

    def test_same_id_with_different_payload_conflicts(self) -> None:
        identifier = uuid4()
        first = command(
            CommandName.ENABLE_SERVO,
            EnableServoPayload(True),
            command_id=identifier,
        )
        conflicting = command(
            CommandName.ENABLE_SERVO,
            EnableServoPayload(False),
            command_id=identifier,
        )
        self.coordinator.handle(first, lease_id=self.lease_id)
        result = self.coordinator.handle(conflicting, lease_id=self.lease_id)
        self.assertEqual(result.status, CommandStatus.REJECTED)
        self.assertEqual(result.error.code, ErrorCode.COMMAND_ID_CONFLICT)

    def test_new_operation_is_rejected_while_motion_is_active(self) -> None:
        self._enable_and_home()
        first = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0),
        )
        second = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=-10.0, speed_units_per_tick=1.0),
        )
        self.coordinator.handle(first, lease_id=self.lease_id)
        result = self.coordinator.handle(second, lease_id=self.lease_id)
        self.assertEqual(result.error.code, ErrorCode.OPERATION_ACTIVE)

    def test_structured_error_and_snapshots_are_serializable(self) -> None:
        request = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=1.0, speed_units_per_tick=1.0),
        )
        result = self.coordinator.handle(request, lease_id=self.lease_id)
        serialized = result.to_dict()
        telemetry = self.coordinator.telemetry().to_dict()
        json.dumps(serialized)
        json.dumps(telemetry)
        self.assertEqual(serialized["error"]["code"], ErrorCode.SERVO_NOT_ENABLED.value)
        self.assertEqual(serialized["state"]["servo"], ServoState.SERVO_DISABLED.value)
        self.assertEqual(telemetry["units"]["position"], "position_units")
        self.assertIn("sequence", telemetry)
        self.assertIn("acquisition_time", telemetry)

    def test_fault_reset_does_not_enable_home_or_resume(self) -> None:
        self.servo.inject_drive_fault()
        reset = command(CommandName.RESET_FAULT, ResetFaultPayload(True))
        result = self.coordinator.handle(reset, lease_id=self.lease_id)
        self.assertEqual(result.status, CommandStatus.SUCCEEDED)
        state = self.coordinator.state
        self.assertEqual(state.servo, ServoState.SERVO_DISABLED)
        self.assertEqual(state.homing, HomingState.UNHOMED)
        self.assertEqual(state.motion, MotionState.IDLE)

    def test_restart_clears_lease_task_enable_and_homing(self) -> None:
        self._enable_and_home()
        move = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0),
        )
        self.coordinator.handle(move, lease_id=self.lease_id)
        self.coordinator.restart()
        state = self.coordinator.state
        self.assertEqual(state.connection, ConnectionState.DISCONNECTED)
        self.assertEqual(state.servo, ServoState.SERVO_DISABLED)
        self.assertEqual(state.homing, HomingState.UNHOMED)
        self.assertEqual(state.motion, MotionState.IDLE)
        replacement = command(CommandName.ENABLE_SERVO, EnableServoPayload(True))
        self.assertEqual(
            self.coordinator.handle(replacement, lease_id=self.lease_id).error.code,
            ErrorCode.LEASE_REQUIRED,
        )

    def test_lease_expiry_requests_stop_faults_and_preserves_enable(self) -> None:
        self._enable_and_home()
        move = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0),
        )
        self.coordinator.handle(move, lease_id=self.lease_id)
        self.servo.advance()
        self.coordinator.expire_control_lease()
        self.assertEqual(self.coordinator.state.motion, MotionState.STOPPING)
        self.assertEqual(self.coordinator.state.servo, ServoState.SERVO_ENABLED)
        self.assertTrue(self.coordinator.state.recovery_required)
        self.servo.advance()
        self.coordinator.refresh()
        self.assertEqual(self.coordinator.state.motion, MotionState.IDLE)
        self.assertEqual(self.coordinator.state.servo, ServoState.SERVO_ENABLED)
        self.assertEqual(
            self.coordinator.result_for(move.command_id).status,
            CommandStatus.CANCELLED,
        )
        rejected = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=-5.0, speed_units_per_tick=1.0),
        )
        self.assertEqual(
            self.coordinator.handle(rejected, lease_id=self.lease_id).error.code,
            ErrorCode.LEASE_REQUIRED,
        )
        recovery_lease = uuid4()
        self.assertTrue(self.coordinator.acquire_control_lease(recovery_lease))
        reset = command(CommandName.RESET_FAULT, ResetFaultPayload(True))
        self.assertEqual(
            self.coordinator.handle(reset, lease_id=recovery_lease).status,
            CommandStatus.SUCCEEDED,
        )
        self.assertFalse(self.coordinator.state.recovery_required)
        self.assertEqual(self.coordinator.state.motion, MotionState.IDLE)

    def test_lease_expiry_with_unavailable_communication_is_distinguishable(self) -> None:
        self._enable_and_home()
        move = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0),
        )
        self.coordinator.handle(move, lease_id=self.lease_id)
        self.servo.advance()
        self.servo.inject_communication_fault()
        self.coordinator.expire_control_lease()
        self.assertEqual(
            self.coordinator.state.connection,
            ConnectionState.COMMUNICATION_FAULT,
        )
        self.assertEqual(
            self.coordinator.state.active_fault_code,
            "CONTROL_LEASE_EXPIRED_STOP_UNCONFIRMED",
        )

    def test_controlled_stop_completes_without_servo_disable(self) -> None:
        self._enable_and_home()
        move = command(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0),
        )
        self.coordinator.handle(move, lease_id=self.lease_id)
        self.servo.advance()
        stop = command(CommandName.CONTROLLED_STOP, ControlledStopPayload())
        self.assertEqual(
            self.coordinator.handle(stop, lease_id=self.lease_id).status,
            CommandStatus.RUNNING,
        )
        self.servo.advance()
        self.coordinator.refresh()
        self.assertEqual(
            self.coordinator.result_for(stop.command_id).status,
            CommandStatus.SUCCEEDED,
        )
        self.assertEqual(self.coordinator.state.servo, ServoState.SERVO_ENABLED)


if __name__ == "__main__":
    unittest.main()
