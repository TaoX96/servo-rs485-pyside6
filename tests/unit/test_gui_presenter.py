"""Pure state and telemetry presentation tests."""

from __future__ import annotations

from datetime import UTC, datetime

from knee_rig.common.models import (
    AuthorizationDecision,
    CommandName,
    ConnectionState,
    HomingState,
    LimitInputState,
    MotionState,
    ServiceState,
    ServoState,
    StateSnapshot,
    TelemetrySnapshot,
)
from knee_rig.gui.client import LeaseSnapshot
from knee_rig.gui.presenter import present


def _state(
    *,
    service: ServiceState = ServiceState.READY,
    connection: ConnectionState = ConnectionState.CONNECTED,
    servo: ServoState = ServoState.SERVO_ENABLED,
    homing: HomingState = HomingState.HOMED,
    motion: MotionState = MotionState.IDLE,
    active_fault_code: str | None = None,
    recovery_required: bool = False,
) -> StateSnapshot:
    return StateSnapshot(
        service=service,
        connection=connection,
        servo=servo,
        homing=homing,
        motion=motion,
        active_fault_code=active_fault_code,
        recovery_required=recovery_required,
    )


def _telemetry(*, valid: bool = True, limits: LimitInputState | None = None) -> TelemetrySnapshot:
    return TelemetrySnapshot(
        sequence=7,
        acquisition_time=datetime(2026, 1, 1, tzinfo=UTC),
        monotonic_s=12.0,
        valid=valid,
        fresh=valid,
        position_units=4.5,
        velocity_units_per_s=2.0,
        torque_percent=3.0,
        limits=limits if limits is not None else LimitInputState(),
        quality_reason=None if valid else "communication_unavailable",
    )


def test_presenter_uses_explicit_units_and_cycle_progress() -> None:
    view = present(
        _state(),
        _telemetry(limits=LimitInputState(pl_active=True, hsw_active=True)),
        LeaseSnapshot(True, expires_in_s=10.0),
        3,
        {CommandName.START_SINGLE_MOVE: AuthorizationDecision(True)},
    )

    assert view.telemetry.position == "4.500 application units"
    assert view.telemetry.velocity == "2.000 application units/s"
    assert view.telemetry.torque == "3.0 %"
    assert view.telemetry.sequence == "7"
    assert view.telemetry.pl == "[ACTIVE] Yes"
    assert view.telemetry.nl == "[INACTIVE] No"
    assert view.telemetry.hsw == "[ACTIVE] Yes"
    assert view.telemetry.cycle_progress == "3 completed cycle(s)"
    assert view.motion_permitted == "[PERMITTED] Yes"


def test_invalid_telemetry_is_unavailable_not_zero() -> None:
    view = present(_state(), _telemetry(valid=False), LeaseSnapshot(False), 0, {})

    assert view.telemetry.position == "Unavailable"
    assert view.telemetry.velocity == "Unavailable"
    assert view.telemetry.torque == "Unavailable"
    assert view.telemetry.timestamp == "Unavailable"
    assert view.telemetry.sequence == "Unavailable"
    assert "communication_unavailable" in view.telemetry.freshness


def test_fault_pause_and_authorization_presentation() -> None:
    state = _state(
        service=ServiceState.FAULT,
        motion=MotionState.MOTION_FAULT,
        active_fault_code="SIMULATED_FAULT",
        recovery_required=True,
    )
    authorizations = {
        CommandName.RESET_FAULT: AuthorizationDecision(True),
        CommandName.START_SINGLE_MOVE: AuthorizationDecision(False),
    }

    view = present(state, _telemetry(), LeaseSnapshot(True, expires_in_s=8.0), 0, authorizations)

    assert "SIMULATED_FAULT" in view.fault
    assert view.motion == "[FAULT] MOTION_FAULT"
    assert view.command_enabled[CommandName.RESET_FAULT]
    assert not view.command_enabled[CommandName.START_SINGLE_MOVE]
    assert view.motion_permitted == "[BLOCKED] No"
