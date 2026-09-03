"""Shared deterministic test builders."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from knee_rig.common.config import (
    AppConfig,
    CalibrationConfig,
    FeatureConfig,
    HomingConfig,
    LimitsConfig,
)
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
        homing=HomingConfig(
            search_direction=1,
            search_speed_units_per_tick=1.0,
            backoff_speed_units_per_tick=1.0,
            search_distance_units=5.0,
            backoff_distance_units=2.0,
            home_offset_units=-2.0,
            search_timeout_ticks=8,
            backoff_timeout_ticks=4,
            drive_internal_mode=18,
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
    assert servo.request_homing(timeout_ticks=20).accepted
    servo.advance(20)
    return servo
