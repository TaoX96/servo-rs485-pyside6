"""Deterministic coverage for the GUI-facing in-process simulation client."""

from __future__ import annotations

from uuid import uuid4

from knee_rig.common.models import (
    CommandName,
    CommandStatus,
    ConnectionState,
    ControlledStopPayload,
    CyclePayload,
    EnableServoPayload,
    ErrorCode,
    HomePayload,
    HomingState,
    MotionState,
    PausePayload,
    ResetFaultPayload,
    ResumePayload,
    ServiceState,
    ServoState,
    SingleMovePayload,
)
from knee_rig.gui.client import InProcessSimulationClient, SimulationFault


def _ready_client() -> InProcessSimulationClient:
    client = InProcessSimulationClient()
    assert client.connect().accepted
    assert client.acquire_lease().accepted
    assert (
        client.submit(CommandName.ENABLE_SERVO, EnableServoPayload(True)).status
        is CommandStatus.SUCCEEDED
    )
    home = client.submit(CommandName.HOME, HomePayload(5))
    assert home.status is CommandStatus.RUNNING
    client.advance(3)
    assert client.state().homing is HomingState.HOMED
    return client


def test_safe_initial_state_and_unavailable_telemetry() -> None:
    client = InProcessSimulationClient()

    state = client.state()
    assert state.connection is ConnectionState.DISCONNECTED
    assert state.servo is ServoState.SERVO_DISABLED
    assert state.homing is HomingState.UNHOMED
    assert state.motion is MotionState.IDLE
    assert not client.telemetry().valid
    assert not any(event.category == "command" for event in client.events())


def test_state_telemetry_command_uuid_and_tick_advancement() -> None:
    client = _ready_client()
    before = client.telemetry().sequence

    move = client.submit(
        CommandName.START_SINGLE_MOVE,
        SingleMovePayload(position_units=5.0, speed_units_per_tick=2.0),
    )

    assert move.command_id.version == 4
    assert move.status is CommandStatus.RUNNING
    client.advance(1)
    assert client.telemetry().sequence == before + 1
    assert client.telemetry().position_units == 2.0
    client.advance(2)
    assert client.state().motion is MotionState.IDLE
    assert client.telemetry().position_units == 5.0


def test_idempotent_replay_and_conflict_are_preserved() -> None:
    client = InProcessSimulationClient()
    client.connect()
    client.acquire_lease()
    command_id = uuid4()

    first = client.submit(CommandName.ENABLE_SERVO, EnableServoPayload(True), command_id=command_id)
    replay = client.submit(
        CommandName.ENABLE_SERVO, EnableServoPayload(True), command_id=command_id
    )
    conflict = client.submit(
        CommandName.ENABLE_SERVO, EnableServoPayload(False), command_id=command_id
    )

    assert replay is first
    assert conflict.status is CommandStatus.REJECTED
    assert conflict.error is not None
    assert conflict.error.code is ErrorCode.COMMAND_ID_CONFLICT


def test_lease_acquire_renew_release_and_expiry() -> None:
    client = InProcessSimulationClient()
    assert client.acquire_lease().accepted
    first_remaining = client.lease().expires_in_s
    client.advance(2)
    assert client.renew_lease().accepted
    assert client.lease().expires_in_s == first_remaining
    assert client.release_lease().accepted
    assert not client.lease().active

    assert client.acquire_lease().accepted
    client.advance(300)
    assert not client.lease().active


def test_fault_injection_and_explicit_recovery() -> None:
    client = _ready_client()
    result = client.inject_fault(SimulationFault.DRIVE_FAULT)

    assert result.accepted
    assert client.state().has_blocking_fault
    reset = client.submit(CommandName.RESET_FAULT, ResetFaultPayload(True))
    assert reset.status is CommandStatus.SUCCEEDED
    assert client.state().servo is ServoState.SERVO_DISABLED
    assert client.state().homing is HomingState.HOMED
    assert client.state().motion is MotionState.IDLE


def test_drive_fault_during_motion_stops_and_fails_active_operation() -> None:
    client = _ready_client()
    payload = SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0)
    move = client.submit(CommandName.START_SINGLE_MOVE, payload)
    client.advance(1)
    assert client.state().motion is MotionState.MOVING
    position_at_fault = client.telemetry().position_units

    assert client.inject_fault(SimulationFault.DRIVE_FAULT).accepted

    state = client.state()
    assert state.service is ServiceState.FAULT
    assert state.servo is ServoState.SERVO_FAULT
    assert state.motion is MotionState.MOTION_FAULT
    assert state.has_blocking_fault
    assert state.active_fault_code == "SIMULATED_DRIVE_FAULT"
    assert state.recovery_required
    for rejected in (
        client.submit(CommandName.START_SINGLE_MOVE, payload),
        client.submit(CommandName.RESUME, ResumePayload(True)),
    ):
        assert rejected.status is CommandStatus.REJECTED
        assert rejected.error is not None
        assert rejected.error.code is ErrorCode.STATE_NOT_AUTHORIZED
    replay = client.submit(CommandName.START_SINGLE_MOVE, payload, command_id=move.command_id)
    assert replay.status is CommandStatus.FAILED
    client.advance(10)
    assert client.telemetry().position_units == position_at_fault
    assert client.state().active_fault_code == "SIMULATED_DRIVE_FAULT"


def test_reset_after_interrupted_motion_never_starts_an_automatic_operation() -> None:
    client = _ready_client()
    payload = SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0)
    move = client.submit(CommandName.START_SINGLE_MOVE, payload)
    client.advance(1)
    client.inject_fault(SimulationFault.DRIVE_FAULT)
    failed = client.submit(CommandName.START_SINGLE_MOVE, payload, command_id=move.command_id)
    assert failed.status is CommandStatus.FAILED

    reset = client.submit(CommandName.RESET_FAULT, ResetFaultPayload(True))

    assert reset.status is CommandStatus.SUCCEEDED
    state = client.state()
    assert state.servo is not ServoState.SERVO_ENABLED
    assert state.homing is not HomingState.HOMING
    assert state.motion not in {MotionState.STARTING, MotionState.MOVING}
    assert state.active_command_id is None
    replay = client.submit(CommandName.START_SINGLE_MOVE, payload, command_id=move.command_id)
    assert replay.status is CommandStatus.FAILED
    new_move = client.submit(CommandName.START_SINGLE_MOVE, payload)
    assert new_move.status is CommandStatus.REJECTED
    assert new_move.error is not None
    assert new_move.error.code is ErrorCode.SERVO_NOT_ENABLED


def test_homing_failure_and_limit_injections() -> None:
    client = InProcessSimulationClient()
    client.connect()
    client.acquire_lease()
    client.submit(CommandName.ENABLE_SERVO, EnableServoPayload(True))
    client.inject_fault(SimulationFault.HSW_NOT_FOUND)
    client.submit(CommandName.HOME, HomePayload(5))
    client.advance(3)
    assert client.state().homing is HomingState.HOMING_FAULT

    second = InProcessSimulationClient()
    second.inject_fault(SimulationFault.PL_AND_NL_ACTIVE)
    assert second.state().has_blocking_fault
    assert second.state().limits.pl_active
    assert second.state().limits.nl_active


def test_contradictory_limits_remain_visible_and_block_recovery_until_cleared() -> None:
    client = _ready_client()
    client.inject_fault(SimulationFault.PL_AND_NL_ACTIVE)

    state = client.state()
    assert state.limits.pl_active and state.limits.nl_active
    assert state.active_fault_code == "LIMIT_STATE_CONTRADICTION"
    assert state.has_blocking_fault
    move = client.submit(
        CommandName.START_SINGLE_MOVE,
        SingleMovePayload(position_units=5.0, speed_units_per_tick=1.0),
    )
    home = client.submit(CommandName.HOME, HomePayload(5))
    reset = client.submit(CommandName.RESET_FAULT, ResetFaultPayload(True))
    for result in (move, home, reset):
        assert result.status is CommandStatus.REJECTED
        assert result.error is not None
        assert result.error.code is ErrorCode.INVALID_LIMIT_STATE
    assert client.state().active_fault_code == "LIMIT_STATE_CONTRADICTION"

    client.inject_fault(SimulationFault.CLEAR_LIMITS)

    cleared = client.state()
    assert not cleared.limits.pl_active and not cleared.limits.nl_active
    assert cleared.active_fault_code == "LIMIT_STATE_CONTRADICTION"
    assert cleared.recovery_required
    assert cleared.servo is not ServoState.SERVO_ENABLING
    assert cleared.homing is not HomingState.HOMING
    assert cleared.motion not in {MotionState.STARTING, MotionState.MOVING}


def test_absolute_motion_farther_into_each_active_limit_is_rejected() -> None:
    cases = (
        (SimulationFault.PL_ACTIVE, 5.0, 6.0),
        (SimulationFault.NL_ACTIVE, -5.0, -6.0),
    )
    for fault, initial_position, target_position in cases:
        client = _ready_client()
        initial = client.submit(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=initial_position, speed_units_per_tick=5.0),
        )
        client.advance(1)
        assert initial.status is CommandStatus.RUNNING
        assert client.telemetry().position_units == initial_position
        client.inject_fault(fault)
        position_before_rejection = client.telemetry().position_units

        rejected = client.submit(
            CommandName.START_SINGLE_MOVE,
            SingleMovePayload(position_units=target_position, speed_units_per_tick=1.0),
        )

        assert rejected.status is CommandStatus.REJECTED
        assert rejected.error is not None
        assert rejected.error.code is ErrorCode.ACTIVE_LIMIT
        assert client.state().motion is MotionState.IDLE
        client.advance(2)
        assert client.telemetry().position_units == position_before_rejection


def test_communication_loss_during_motion_reports_stop_unconfirmed_and_no_recovery() -> None:
    client = _ready_client()
    payload = SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0)
    move = client.submit(CommandName.START_SINGLE_MOVE, payload)
    client.advance(1)
    assert client.state().motion is MotionState.MOVING

    client.inject_fault(SimulationFault.COMMUNICATION_LOSS)
    assert client.state().connection is ConnectionState.COMMUNICATION_FAULT
    assert (
        client.submit(CommandName.START_SINGLE_MOVE, payload, command_id=move.command_id).status
        is CommandStatus.FAILED
    )

    faulted = client.state()
    assert faulted.active_fault_code == "COMMUNICATION_FAULT_STOP_UNCONFIRMED"
    assert faulted.recovery_required
    assert any("cannot confirm a controlled stop" in alarm.message for alarm in client.alarms())
    assert not any("controlled stop was requested" in alarm.message for alarm in client.alarms())
    for name, command_payload in (
        (CommandName.START_SINGLE_MOVE, payload),
        (CommandName.HOME, HomePayload(5)),
        (CommandName.RESUME, ResumePayload(True)),
    ):
        rejected = client.submit(name, command_payload)
        assert rejected.status is CommandStatus.REJECTED
        assert rejected.error is not None
        assert rejected.error.code is ErrorCode.STATE_NOT_AUTHORIZED

    before_reconnect = client.state()
    assert client.connect().accepted
    reconnected = client.state()
    assert reconnected.connection is ConnectionState.CONNECTED
    assert reconnected.servo is before_reconnect.servo
    assert reconnected.homing is not HomingState.HOMING
    assert reconnected.motion not in {MotionState.STARTING, MotionState.MOVING}
    assert reconnected.recovery_required


def test_motion_lease_expiry_requests_controlled_stop_and_requires_recovery() -> None:
    client = _ready_client()
    client.submit(
        CommandName.START_SINGLE_MOVE,
        SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0),
    )
    client.advance(1)

    client.inject_fault(SimulationFault.CONTROL_LEASE_EXPIRY)

    assert client.state().motion is MotionState.STOPPING
    assert client.state().servo is ServoState.SERVO_ENABLED
    assert client.state().recovery_required
    client.advance(1)
    assert client.state().motion is MotionState.IDLE


def test_finite_cycle_pause_explicit_resume_and_controlled_stop() -> None:
    client = _ready_client()
    cycle = client.submit(
        CommandName.START_CYCLE,
        CyclePayload(
            positive_position_units=3.0,
            negative_position_units=-3.0,
            speed_units_per_tick=1.0,
            cycle_count=2,
        ),
    )
    assert cycle.status is CommandStatus.RUNNING
    client.advance(1)
    assert client.submit(CommandName.PAUSE, PausePayload()).status is CommandStatus.SUCCEEDED
    paused_position = client.telemetry().position_units
    client.advance(2)
    assert client.telemetry().position_units == paused_position
    assert client.submit(CommandName.RESUME, ResumePayload(True)).status is CommandStatus.SUCCEEDED
    client.advance(2)
    stop = client.submit(CommandName.CONTROLLED_STOP, ControlledStopPayload())
    assert stop.status is CommandStatus.RUNNING
    client.advance(1)
    assert client.state().motion is MotionState.IDLE
    assert client.state().servo is ServoState.SERVO_ENABLED


def test_event_history_is_bounded() -> None:
    client = InProcessSimulationClient()
    for _ in range(120):
        client.inject_fault(SimulationFault.HSW_NOT_FOUND)
    assert len(client.events()) == 100
