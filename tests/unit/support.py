"""Shared deterministic test builders."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from knee_rig.common.config import AppConfig, CalibrationConfig, FeatureConfig, LimitsConfig
from knee_rig.common.config.models import default_config
from knee_rig.common.models import CommandEnvelope, CommandName, CommandPayload
from knee_rig.motion.simulation import FakeServo


def enabled_simulation_config(*, calibration_verified: bool = True) -> AppConfig:
    return replace(
        default_config(),
        features=FeatureConfig(
            simulation=True,
            allow_servo_enable=True,
            allow_motion=True,
            allow_homing=True,
            allow_persistent_parameter_write=False,
            calibration_verified=calibration_verified,
        ),
        calibration=CalibrationConfig(
            position_units_per_joint_degree=2.0 if calibration_verified else 0.0,
            joint_zero_offset_deg=0.0,
            direction_sign=1 if calibration_verified else 0,
        ),
        limits=replace(
            LimitsConfig(),
            min_joint_angle_deg=-45.0,
            max_joint_angle_deg=45.0,
            max_cycle_count=5,
        ),
    )


def command(
    name: CommandName,
    payload: CommandPayload,
    *,
    command_id: UUID | None = None,
) -> CommandEnvelope:
    return CommandEnvelope(command_id or uuid4(), name, payload)


def connected_enabled_homed_servo() -> FakeServo:
    servo = FakeServo()
    assert servo.connect().accepted
    assert servo.request_servo_enable().accepted
    assert servo.request_homing(timeout_ticks=5).accepted
    servo.advance(3)
    return servo

