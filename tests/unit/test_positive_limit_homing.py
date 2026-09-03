"""Deterministic positive-limit reference homing behavior and failure boundaries."""

from __future__ import annotations

from dataclasses import replace

import pytest

from knee_rig.common.config import HomingConfig
from knee_rig.common.models import HomingPhase, HomingState, MotionState, ServoState
from knee_rig.motion.simulation import FakeServo, HomingFailure


def _started(
    failure: HomingFailure | None = None,
    *,
    homing_config: HomingConfig | None = None,
    timeout_ticks: int = 20,
) -> FakeServo:
    servo = FakeServo(homing_config=homing_config)
    assert servo.connect().accepted
    assert servo.request_servo_enable().accepted
    servo.set_next_homing_failure(failure)
    assert servo.request_homing(timeout_ticks=timeout_ticks).accepted
    return servo


def test_pl_detection_stop_backoff_release_offset_and_completion() -> None:
    servo = _started()
    status = servo.read_status()
    assert status.homing_strategy.value == "POSITIVE_LIMIT_REFERENCE"
    assert servo.read_status().homing_phase is HomingPhase.SEARCHING_POSITIVE_LIMIT

    servo.advance(2)
    detected = servo.read_status()
    assert detected.limits.pl_active
    assert detected.homing_phase is HomingPhase.CONTROLLED_STOP_AT_LIMIT
    assert detected.homing is HomingState.HOMING

    servo.advance(2)
    released = servo.read_status()
    assert not released.limits.pl_active
    assert released.homing_phase is HomingPhase.BACKING_OFF_POSITIVE_LIMIT
    assert released.homing is HomingState.HOMING

    servo.advance(3)
    before_completion = servo.read_status()
    assert before_completion.homing_phase is HomingPhase.VERIFYING_COMPLETION
    assert before_completion.homing is HomingState.HOMING

    servo.advance(1)
    complete = servo.read_status()
    assert complete.homing is HomingState.HOMED
    assert complete.homing_phase is HomingPhase.COMPLETE
    assert complete.motion is MotionState.IDLE
    assert not complete.limits.pl_active
    assert servo.read_telemetry().position_units == 0.0


@pytest.mark.parametrize(
    ("failure", "ticks", "code"),
    [
        (HomingFailure.PL_NEVER_FOUND, 5, "PL_NOT_FOUND"),
        (HomingFailure.TIMEOUT, 8, "HOMING_SEARCH_TIMEOUT"),
        (HomingFailure.PL_STUCK_ACTIVE, 5, "PL_STUCK_ACTIVE"),
        (HomingFailure.BACKOFF_TIMEOUT, 7, "HOMING_BACKOFF_TIMEOUT"),
        (
            HomingFailure.CONTROLLED_STOP_UNCONFIRMED,
            3,
            "HOMING_CONTROLLED_STOP_UNCONFIRMED",
        ),
    ],
)
def test_homing_failures_never_mark_homed(
    failure: HomingFailure,
    ticks: int,
    code: str,
) -> None:
    servo = _started(failure)
    servo.advance(ticks)
    state = servo.read_status()
    assert state.homing is HomingState.HOMING_FAULT
    assert state.homing_phase is HomingPhase.FAULT
    assert state.active_fault_code == code
    servo.advance(20)
    assert servo.read_status().homing is HomingState.HOMING_FAULT


def test_overall_homing_timeout_is_distinct() -> None:
    servo = _started(timeout_ticks=2)
    servo.advance(2)
    assert servo.read_status().active_fault_code == "HOMING_TIMEOUT"


@pytest.mark.parametrize("advance_ticks", [0, 2, 3, 5, 7])
def test_communication_loss_during_every_phase_stops_and_never_restarts(
    advance_ticks: int,
) -> None:
    servo = _started()
    servo.advance(advance_ticks)
    servo.inject_communication_fault()
    position = servo.read_telemetry().position_units
    servo.advance(20)
    state = servo.read_status()
    assert state.homing is not HomingState.HOMED
    assert state.motion is MotionState.MOTION_FAULT
    assert servo.read_telemetry().position_units == position
    assert servo.reconnect_after_communication_fault().accepted
    assert servo.read_status().homing is not HomingState.HOMING


@pytest.mark.parametrize("advance_ticks", [0, 2, 3, 5, 7])
def test_drive_fault_during_every_phase_stops_and_never_restarts(advance_ticks: int) -> None:
    servo = _started()
    servo.advance(advance_ticks)
    servo.inject_drive_fault()
    position = servo.read_telemetry().position_units
    servo.advance(20)
    state = servo.read_status()
    assert state.servo is ServoState.SERVO_FAULT
    assert state.homing is HomingState.HOMING_FAULT
    assert state.motion is MotionState.MOTION_FAULT
    assert servo.read_telemetry().position_units == position
    assert servo.reset_fault().accepted
    recovered = servo.read_status()
    assert recovered.servo is ServoState.SERVO_DISABLED
    assert recovered.homing is HomingState.UNHOMED
    assert recovered.motion is MotionState.IDLE


def test_pl_active_at_start_is_rejected_without_escape_recovery() -> None:
    servo = FakeServo()
    servo.connect()
    servo.request_servo_enable()
    servo.set_limits(pl_active=True, nl_active=False, hsw_active=False)
    result = servo.request_homing(timeout_ticks=20)
    assert not result.accepted
    assert result.code == "PL_ACTIVE_AT_START"
    assert servo.read_status().homing is HomingState.UNHOMED


def test_contradictory_limits_reject_homing() -> None:
    servo = FakeServo()
    servo.connect()
    servo.request_servo_enable()
    servo.set_limits(pl_active=True, nl_active=True, hsw_active=False)
    result = servo.request_homing(timeout_ticks=20)
    assert not result.accepted
    assert result.code == "FAULT_ACTIVE"
    assert servo.read_status().active_fault_code == "LIMIT_STATE_CONTRADICTION"
    assert servo.read_status().homing is not HomingState.HOMING


def test_negative_backoff_occurs_only_inside_active_homing_operation() -> None:
    idle = FakeServo()
    idle.connect()
    idle.request_servo_enable()
    idle.set_limits(pl_active=True, nl_active=False, hsw_active=False)
    initial_position = idle.read_telemetry().position_units
    idle.advance(5)
    assert idle.read_telemetry().position_units == initial_position

    homing = _started()
    homing.advance(3)
    before_backoff = homing.read_telemetry().position_units
    assert homing.read_status().homing_phase is HomingPhase.BACKING_OFF_POSITIVE_LIMIT
    homing.advance(1)
    assert homing.read_telemetry().position_units < before_backoff
    assert homing.read_status().homing is HomingState.HOMING


def test_fault_recovery_never_starts_enable_homing_or_motion() -> None:
    servo = _started(HomingFailure.PL_STUCK_ACTIVE)
    servo.advance(5)
    assert servo.reset_fault().accepted
    recovered = servo.read_status()
    assert recovered.servo is ServoState.SERVO_ENABLED
    assert recovered.homing is HomingState.UNHOMED
    assert recovered.motion is MotionState.IDLE
    position = servo.read_telemetry().position_units
    servo.advance(20)
    assert servo.read_telemetry().position_units == position
    assert servo.read_status() == recovered


def test_wrong_offset_direction_is_defensively_rejected() -> None:
    valid = HomingConfig(
        search_speed_units_per_tick=1.0,
        backoff_speed_units_per_tick=1.0,
        search_distance_units=5.0,
        backoff_distance_units=2.0,
        home_offset_units=-2.0,
        search_timeout_ticks=8,
        backoff_timeout_ticks=4,
    )
    servo = FakeServo(homing_config=replace(valid, home_offset_units=2.0))
    servo.connect()
    servo.request_servo_enable()
    result = servo.request_homing(timeout_ticks=20)
    assert not result.accepted
    assert result.code == "HOMING_CONFIG_INVALID"
