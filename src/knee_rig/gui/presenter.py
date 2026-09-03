"""Pure presentation logic shared by the Qt window and deterministic tests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from knee_rig.common.models import (
    AuthorizationDecision,
    CommandName,
    ConnectionState,
    HomingState,
    MotionState,
    ServiceState,
    ServoState,
    StateSnapshot,
    TelemetrySnapshot,
)
from knee_rig.gui.client.interface import LeaseSnapshot


@dataclass(frozen=True, slots=True)
class TelemetryView:
    position: str
    velocity: str
    torque: str
    timestamp: str
    sequence: str
    freshness: str
    pl: str
    nl: str
    hsw: str
    cycle_progress: str


@dataclass(frozen=True, slots=True)
class MainView:
    service: str
    connection: str
    servo: str
    homing: str
    homing_reference: str
    homing_phase: str
    motion: str
    lease: str
    motion_permitted: str
    fault: str
    telemetry: TelemetryView
    command_enabled: dict[CommandName, bool]


def present(
    state: StateSnapshot,
    telemetry: TelemetrySnapshot,
    lease: LeaseSnapshot,
    completed_cycles: int,
    authorizations: Mapping[CommandName, AuthorizationDecision],
) -> MainView:
    """Render explicit units and authorization without changing simulation state."""
    enabled = {name: decision.allowed for name, decision in authorizations.items()}
    motion_allowed = enabled.get(CommandName.START_SINGLE_MOVE, False) or enabled.get(
        CommandName.START_CYCLE, False
    )
    if telemetry.valid:
        position = f"{telemetry.position_units:.3f} application units"
        velocity = f"{telemetry.velocity_units_per_s:.3f} application units/s"
        torque = f"{telemetry.torque_percent:.1f} %"
        timestamp = telemetry.acquisition_time.isoformat()
        sequence = str(telemetry.sequence)
        freshness = "VALID / FRESH" if telemetry.fresh else "VALID / STALE"
    else:
        position = velocity = torque = timestamp = sequence = "Unavailable"
        reason = telemetry.quality_reason or "invalid telemetry"
        freshness = f"UNAVAILABLE — {reason}"
    return MainView(
        service=_state_text(state.service, ServiceState.READY),
        connection=_state_text(state.connection, ConnectionState.CONNECTED),
        servo=_state_text(state.servo, ServoState.SERVO_ENABLED),
        homing=_state_text(state.homing, HomingState.HOMED),
        homing_reference="PL (positive travel limit; HSW and encoder index deferred)",
        homing_phase=state.homing_phase.value,
        motion=_motion_text(state.motion),
        lease=(
            f"[ACTIVE] {lease.expires_in_s:.0f} s remaining"
            if lease.active and lease.expires_in_s is not None
            else "[INACTIVE] No control lease"
        ),
        motion_permitted="[PERMITTED] Yes" if motion_allowed else "[BLOCKED] No",
        fault=(
            f"[FAULT] {state.active_fault_code or 'Explicit recovery required'}"
            if state.has_blocking_fault
            else "[CLEAR] None"
        ),
        telemetry=TelemetryView(
            position=position,
            velocity=velocity,
            torque=torque,
            timestamp=timestamp,
            sequence=sequence,
            freshness=freshness,
            pl=_input_text(telemetry.limits.pl_active),
            nl=_input_text(telemetry.limits.nl_active),
            hsw=_input_text(telemetry.limits.hsw_active),
            cycle_progress=f"{completed_cycles} completed cycle(s)",
        ),
        command_enabled=enabled,
    )


def _state_text(value: object, preferred: object) -> str:
    name = getattr(value, "value", str(value))
    return f"[OK] {name}" if value is preferred else f"[STATE] {name}"


def _motion_text(motion: MotionState) -> str:
    cue = {
        MotionState.IDLE: "IDLE",
        MotionState.STARTING: "ACTIVE",
        MotionState.MOVING: "ACTIVE",
        MotionState.PAUSED: "PAUSED",
        MotionState.STOPPING: "STOPPING",
        MotionState.MOTION_FAULT: "FAULT",
    }[motion]
    return f"[{cue}] {motion.value}"


def _input_text(active: bool) -> str:
    return "[ACTIVE] Yes" if active else "[INACTIVE] No"
