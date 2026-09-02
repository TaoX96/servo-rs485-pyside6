"""FakeServo scenarios advance only through explicit deterministic ticks."""

from __future__ import annotations

import unittest

from knee_rig.common.models import (
    ConnectionState,
    HomingState,
    MotionState,
    ServoState,
)
from knee_rig.motion.simulation import FakeServo, HomingFailure
from tests.unit.support import connected_enabled_homed_servo


class FakeServoTests(unittest.TestCase):
    def test_safe_startup_and_explicit_connection(self) -> None:
        servo = FakeServo()
        initial = servo.read_status()
        self.assertEqual(initial.connection, ConnectionState.DISCONNECTED)
        self.assertEqual(initial.servo, ServoState.SERVO_DISABLED)
        self.assertEqual(initial.homing, HomingState.UNHOMED)
        self.assertEqual(initial.motion, MotionState.IDLE)
        self.assertFalse(servo.request_servo_enable().accepted)

        self.assertTrue(servo.connect().accepted)
        connected = servo.read_status()
        self.assertEqual(connected.connection, ConnectionState.CONNECTED)
        self.assertEqual(connected.servo, ServoState.SERVO_DISABLED)
        self.assertEqual(connected.homing, HomingState.UNHOMED)

    def test_explicit_enable_and_successful_homing(self) -> None:
        servo = FakeServo()
        servo.connect()
        self.assertTrue(servo.request_servo_enable().accepted)
        self.assertEqual(servo.read_status().servo, ServoState.SERVO_ENABLED)
        receipt = servo.request_homing(timeout_ticks=5)
        self.assertTrue(receipt.accepted)
        self.assertFalse(receipt.completed)
        servo.advance(3)
        self.assertEqual(servo.read_status().homing, HomingState.HOMED)
        self.assertTrue(servo.read_status().limits.hsw_active)

    def test_homing_timeout(self) -> None:
        servo = FakeServo()
        servo.connect()
        servo.request_servo_enable()
        servo.request_homing(timeout_ticks=2)
        servo.advance(2)
        self.assertEqual(servo.read_status().homing, HomingState.HOMING_FAULT)
        self.assertEqual(servo.read_status().active_fault_code, "HOMING_TIMEOUT")

    def test_hsw_not_found(self) -> None:
        servo = FakeServo()
        servo.connect()
        servo.request_servo_enable()
        servo.set_next_homing_failure(HomingFailure.HSW_NOT_FOUND)
        servo.request_homing(timeout_ticks=5)
        servo.advance(3)
        self.assertEqual(servo.read_status().homing, HomingState.HOMING_FAULT)
        self.assertEqual(servo.read_status().active_fault_code, "HSW_NOT_FOUND")

    def test_single_bounded_move(self) -> None:
        servo = connected_enabled_homed_servo()
        receipt = servo.start_single_move(position_units=3.0, speed_units_per_tick=1.0)
        self.assertTrue(receipt.accepted)
        servo.advance(3)
        self.assertEqual(servo.read_status().motion, MotionState.IDLE)
        self.assertEqual(servo.read_telemetry().position_units, 3.0)
        self.assertEqual(servo.read_telemetry().velocity_units_per_s, 0.0)

    def test_finite_cycle_count(self) -> None:
        servo = connected_enabled_homed_servo()
        receipt = servo.start_cycle(
            positive_position_units=2.0,
            negative_position_units=-2.0,
            speed_units_per_tick=1.0,
            cycle_count=2,
        )
        self.assertTrue(receipt.accepted)
        servo.advance(20)
        self.assertEqual(servo.completed_cycles, 2)
        self.assertEqual(servo.read_status().motion, MotionState.IDLE)
        self.assertEqual(servo.read_telemetry().position_units, -2.0)

    def test_pause_requires_explicit_resume(self) -> None:
        servo = connected_enabled_homed_servo()
        servo.start_single_move(position_units=5.0, speed_units_per_tick=1.0)
        servo.advance()
        paused_at = servo.read_telemetry().position_units
        self.assertTrue(servo.pause().accepted)
        servo.advance(3)
        self.assertEqual(servo.read_status().motion, MotionState.PAUSED)
        self.assertEqual(servo.read_telemetry().position_units, paused_at)
        self.assertTrue(servo.resume().accepted)
        servo.advance(10)
        self.assertEqual(servo.read_status().motion, MotionState.IDLE)
        self.assertEqual(servo.read_telemetry().position_units, 5.0)

    def test_controlled_stop_is_observable_and_does_not_disable(self) -> None:
        servo = connected_enabled_homed_servo()
        servo.start_single_move(position_units=5.0, speed_units_per_tick=1.0)
        servo.advance()
        self.assertTrue(servo.request_controlled_stop().accepted)
        self.assertEqual(servo.read_status().motion, MotionState.STOPPING)
        servo.advance()
        self.assertEqual(servo.read_status().motion, MotionState.IDLE)
        self.assertEqual(servo.read_status().servo, ServoState.SERVO_ENABLED)

    def test_fault_injection_never_auto_recovers(self) -> None:
        servo = connected_enabled_homed_servo()
        servo.inject_drive_fault()
        self.assertEqual(servo.read_status().servo, ServoState.SERVO_FAULT)
        servo.advance(5)
        self.assertEqual(servo.read_status().servo, ServoState.SERVO_FAULT)
        self.assertIsNotNone(servo.read_status().active_fault_code)

    def test_communication_loss_invalidates_motion_and_reconnect_does_not_resume(self) -> None:
        servo = connected_enabled_homed_servo()
        servo.start_single_move(position_units=5.0, speed_units_per_tick=1.0)
        servo.advance()
        servo.inject_communication_fault()
        self.assertEqual(servo.read_status().connection, ConnectionState.COMMUNICATION_FAULT)
        self.assertEqual(servo.read_status().motion, MotionState.MOTION_FAULT)
        self.assertTrue(servo.reconnect_after_communication_fault().accepted)
        self.assertEqual(servo.read_status().connection, ConnectionState.CONNECTED)
        self.assertEqual(servo.read_status().motion, MotionState.MOTION_FAULT)
        self.assertEqual(servo.read_status().homing, HomingState.UNHOMED)

    def test_limits_can_be_injected_and_contradiction_faults(self) -> None:
        servo = connected_enabled_homed_servo()
        servo.set_limits(pl_active=True, nl_active=True, hsw_active=False)
        self.assertEqual(servo.read_status().active_fault_code, "LIMIT_STATE_CONTRADICTION")

    def test_limit_activation_during_motion_faults(self) -> None:
        servo = connected_enabled_homed_servo()
        servo.start_single_move(position_units=5.0, speed_units_per_tick=1.0)
        servo.advance()
        servo.set_limits(pl_active=True, nl_active=False, hsw_active=False)
        self.assertEqual(servo.read_status().motion, MotionState.MOTION_FAULT)
        self.assertEqual(
            servo.read_status().active_fault_code,
            "LIMIT_ACTIVATED_DURING_MOTION",
        )

    def test_negative_limit_activation_during_motion_faults(self) -> None:
        servo = connected_enabled_homed_servo()
        servo.start_single_move(position_units=-5.0, speed_units_per_tick=1.0)
        servo.advance()
        servo.set_limits(pl_active=False, nl_active=True, hsw_active=False)
        self.assertEqual(servo.read_status().motion, MotionState.MOTION_FAULT)
        self.assertEqual(
            servo.read_status().active_fault_code,
            "LIMIT_ACTIVATED_DURING_MOTION",
        )


if __name__ == "__main__":
    unittest.main()
