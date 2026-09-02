"""Strict TOML layering for the shared, Pi, and Windows configuration files."""

from __future__ import annotations

import math
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from knee_rig.common.config.models import (
    AppConfig,
    CalibrationConfig,
    FeatureConfig,
    GuiConfig,
    LimitsConfig,
    LoggingConfig,
    MonitoringApiConfig,
    MonitoringServiceConfig,
    MotionApiConfig,
    MotionServiceConfig,
    SerialConfig,
    default_config,
)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    path: str
    message: str


class ConfigValidationError(ValueError):
    """Raised with all clear, stable validation issues found in a configuration."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        message = "; ".join(
            f"{issue.code} at {issue.path}: {issue.message}" for issue in self.issues
        )
        super().__init__(message)

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self.issues)


def load_config(
    *,
    shared_paths: Iterable[Path] = (),
    local_paths: Iterable[Path] = (),
) -> AppConfig:
    """Load built-ins, required shared layers, then optional machine-local layers."""
    merged = cast(dict[str, object], asdict(default_config()))
    issues: list[ValidationIssue] = []

    for path in shared_paths:
        layer = _read_toml(path, required=True, issues=issues)
        if layer is not None:
            _merge_known(merged, layer, "", issues)

    for path in local_paths:
        layer = _read_toml(path, required=False, issues=issues)
        if layer is not None:
            _merge_known(merged, layer, "", issues)

    if issues:
        raise ConfigValidationError(issues)

    config = _build_config(merged)
    _validate_config(config)
    return config


def _read_toml(
    path: Path,
    *,
    required: bool,
    issues: list[ValidationIssue],
) -> dict[str, object] | None:
    if not path.exists():
        if required:
            issues.append(
                ValidationIssue(
                    "CONFIG_FILE_MISSING",
                    str(path),
                    "required configuration is absent",
                )
            )
        return None
    try:
        return cast(dict[str, object], tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        issues.append(ValidationIssue("CONFIG_READ_ERROR", str(path), str(exc)))
        return None


def _merge_known(
    target: dict[str, object],
    layer: Mapping[str, object],
    prefix: str,
    issues: list[ValidationIssue],
) -> None:
    for key, incoming in layer.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in target:
            issues.append(ValidationIssue("UNKNOWN_FIELD", path, "field is not in the schema"))
            continue
        existing = target[key]
        if isinstance(existing, dict):
            if not isinstance(incoming, dict):
                issues.append(ValidationIssue("INVALID_TYPE", path, "expected a TOML table"))
                continue
            _merge_known(existing, cast(dict[str, object], incoming), path, issues)
        else:
            target[key] = incoming


def _section(data: Mapping[str, object], name: str) -> Mapping[str, object]:
    value = data[name]
    if not isinstance(value, dict):
        raise ConfigValidationError(
            [ValidationIssue("INVALID_TYPE", name, "expected a TOML table")]
        )
    return cast(dict[str, object], value)


def _bool(data: Mapping[str, object], key: str, path: str) -> bool:
    value = data[key]
    if type(value) is not bool:
        raise ConfigValidationError(
            [ValidationIssue("INVALID_TYPE", path, "expected a boolean")]
        )
    return value


def _str(data: Mapping[str, object], key: str, path: str) -> str:
    value = data[key]
    if type(value) is not str:
        raise ConfigValidationError([ValidationIssue("INVALID_TYPE", path, "expected a string")])
    return value


def _int(data: Mapping[str, object], key: str, path: str) -> int:
    value = data[key]
    if type(value) is not int:
        raise ConfigValidationError([ValidationIssue("INVALID_TYPE", path, "expected an integer")])
    return value


def _float(data: Mapping[str, object], key: str, path: str) -> float:
    value = data[key]
    if type(value) not in (int, float):
        raise ConfigValidationError([ValidationIssue("INVALID_TYPE", path, "expected a number")])
    return float(cast(int | float, value))


def _build_config(data: Mapping[str, object]) -> AppConfig:
    features = _section(data, "features")
    calibration = _section(data, "calibration")
    limits = _section(data, "limits")
    logging = _section(data, "logging")
    motion_service = _section(data, "motion_service")
    serial = _section(data, "serial")
    monitoring_service = _section(data, "monitoring_service")
    motion_api = _section(data, "motion_api")
    monitoring_api = _section(data, "monitoring_api")
    gui = _section(data, "gui")

    return AppConfig(
        features=FeatureConfig(
            simulation=_bool(features, "simulation", "features.simulation"),
            allow_servo_enable=_bool(
                features, "allow_servo_enable", "features.allow_servo_enable"
            ),
            allow_motion=_bool(features, "allow_motion", "features.allow_motion"),
            allow_homing=_bool(features, "allow_homing", "features.allow_homing"),
            allow_persistent_parameter_write=_bool(
                features,
                "allow_persistent_parameter_write",
                "features.allow_persistent_parameter_write",
            ),
            calibration_verified=_bool(
                features, "calibration_verified", "features.calibration_verified"
            ),
        ),
        calibration=CalibrationConfig(
            position_units_per_joint_degree=_float(
                calibration,
                "position_units_per_joint_degree",
                "calibration.position_units_per_joint_degree",
            ),
            joint_zero_offset_deg=_float(
                calibration, "joint_zero_offset_deg", "calibration.joint_zero_offset_deg"
            ),
            direction_sign=_int(calibration, "direction_sign", "calibration.direction_sign"),
        ),
        limits=LimitsConfig(
            min_joint_angle_deg=_float(
                limits, "min_joint_angle_deg", "limits.min_joint_angle_deg"
            ),
            max_joint_angle_deg=_float(
                limits, "max_joint_angle_deg", "limits.max_joint_angle_deg"
            ),
            max_motor_speed_rpm=_int(
                limits, "max_motor_speed_rpm", "limits.max_motor_speed_rpm"
            ),
            min_acceleration_time_ms=_int(
                limits, "min_acceleration_time_ms", "limits.min_acceleration_time_ms"
            ),
            min_deceleration_time_ms=_int(
                limits, "min_deceleration_time_ms", "limits.min_deceleration_time_ms"
            ),
            max_wait_time_ms=_int(limits, "max_wait_time_ms", "limits.max_wait_time_ms"),
            max_cycle_count=_int(limits, "max_cycle_count", "limits.max_cycle_count"),
            max_motor_temperature_c=_float(
                limits, "max_motor_temperature_c", "limits.max_motor_temperature_c"
            ),
            max_encoder_temperature_c=_float(
                limits, "max_encoder_temperature_c", "limits.max_encoder_temperature_c"
            ),
            max_torque_percent=_float(
                limits, "max_torque_percent", "limits.max_torque_percent"
            ),
        ),
        logging=LoggingConfig(
            level=_str(logging, "level", "logging.level"),
            directory=_str(logging, "directory", "logging.directory"),
        ),
        motion_service=MotionServiceConfig(
            bind_host=_str(motion_service, "bind_host", "motion_service.bind_host"),
            port=_int(motion_service, "port", "motion_service.port"),
            control_lease_ttl_s=_float(
                motion_service, "control_lease_ttl_s", "motion_service.control_lease_ttl_s"
            ),
        ),
        serial=SerialConfig(
            device=_str(serial, "device", "serial.device"),
            protocol=_str(serial, "protocol", "serial.protocol"),
            slave_address=_int(serial, "slave_address", "serial.slave_address"),
            baudrate=_int(serial, "baudrate", "serial.baudrate"),
            data_bits=_int(serial, "data_bits", "serial.data_bits"),
            parity=_str(serial, "parity", "serial.parity"),
            stop_bits=_int(serial, "stop_bits", "serial.stop_bits"),
            timeout_s=_float(serial, "timeout_s", "serial.timeout_s"),
            byteorder_32=_str(serial, "byteorder_32", "serial.byteorder_32"),
            legacy_byteorder_hypothesis=_str(
                serial,
                "legacy_byteorder_hypothesis",
                "serial.legacy_byteorder_hypothesis",
            ),
        ),
        monitoring_service=MonitoringServiceConfig(
            bind_host=_str(
                monitoring_service, "bind_host", "monitoring_service.bind_host"
            ),
            port=_int(monitoring_service, "port", "monitoring_service.port"),
            allow_camera=_bool(
                monitoring_service, "allow_camera", "monitoring_service.allow_camera"
            ),
            allow_recording=_bool(
                monitoring_service, "allow_recording", "monitoring_service.allow_recording"
            ),
            allow_temperature_sensor=_bool(
                monitoring_service,
                "allow_temperature_sensor",
                "monitoring_service.allow_temperature_sensor",
            ),
            media_directory=_str(
                monitoring_service, "media_directory", "monitoring_service.media_directory"
            ),
        ),
        motion_api=MotionApiConfig(
            base_url=_str(motion_api, "base_url", "motion_api.base_url"),
            request_timeout_s=_float(
                motion_api, "request_timeout_s", "motion_api.request_timeout_s"
            ),
            lease_renewal_interval_s=_float(
                motion_api,
                "lease_renewal_interval_s",
                "motion_api.lease_renewal_interval_s",
            ),
        ),
        monitoring_api=MonitoringApiConfig(
            base_url=_str(monitoring_api, "base_url", "monitoring_api.base_url"),
            request_timeout_s=_float(
                monitoring_api, "request_timeout_s", "monitoring_api.request_timeout_s"
            ),
            temperature_interval_s=_float(
                monitoring_api,
                "temperature_interval_s",
                "monitoring_api.temperature_interval_s",
            ),
        ),
        gui=GuiConfig(
            start_maximized=_bool(gui, "start_maximized", "gui.start_maximized"),
            confirm_state_changing_commands=_bool(
                gui,
                "confirm_state_changing_commands",
                "gui.confirm_state_changing_commands",
            ),
        ),
    )


def _validate_config(config: AppConfig) -> None:
    issues: list[ValidationIssue] = []
    features = config.features
    calibration = config.calibration
    limits = config.limits

    numeric_values = {
        "calibration.position_units_per_joint_degree": calibration.position_units_per_joint_degree,
        "calibration.joint_zero_offset_deg": calibration.joint_zero_offset_deg,
        "limits.min_joint_angle_deg": limits.min_joint_angle_deg,
        "limits.max_joint_angle_deg": limits.max_joint_angle_deg,
        "limits.max_motor_temperature_c": limits.max_motor_temperature_c,
        "limits.max_encoder_temperature_c": limits.max_encoder_temperature_c,
        "limits.max_torque_percent": limits.max_torque_percent,
        "motion_service.control_lease_ttl_s": config.motion_service.control_lease_ttl_s,
        "serial.timeout_s": config.serial.timeout_s,
        "motion_api.request_timeout_s": config.motion_api.request_timeout_s,
        "motion_api.lease_renewal_interval_s": config.motion_api.lease_renewal_interval_s,
        "monitoring_api.request_timeout_s": config.monitoring_api.request_timeout_s,
        "monitoring_api.temperature_interval_s": config.monitoring_api.temperature_interval_s,
    }
    for path, number in numeric_values.items():
        if not math.isfinite(number):
            issues.append(ValidationIssue("NON_FINITE_NUMBER", path, "must be finite"))

    if features.allow_persistent_parameter_write:
        issues.append(
            ValidationIssue(
                "PERSISTENT_WRITES_UNAVAILABLE",
                "features.allow_persistent_parameter_write",
                "Milestone 1 cannot authorize persistent writes",
            )
        )
    if features.allow_motion and not features.allow_servo_enable:
        issues.append(
            ValidationIssue(
                "INCONSISTENT_FEATURE_GATES",
                "features.allow_motion",
                "motion requires the simulation servo-enable gate",
            )
        )
    if features.allow_motion and not features.allow_homing:
        issues.append(
            ValidationIssue(
                "INCONSISTENT_FEATURE_GATES",
                "features.allow_motion",
                "automatic motion requires the simulation homing gate",
            )
        )
    if features.calibration_verified:
        if calibration.position_units_per_joint_degree <= 0:
            issues.append(
                ValidationIssue(
                    "INVALID_CALIBRATION",
                    "calibration.position_units_per_joint_degree",
                    "verified calibration requires a positive non-zero factor",
                )
            )
        if calibration.direction_sign not in (-1, 1):
            issues.append(
                ValidationIssue(
                    "INVALID_CALIBRATION",
                    "calibration.direction_sign",
                    "verified calibration requires -1 or 1",
                )
            )

    if (
        limits.min_joint_angle_deg != 0.0
        or limits.max_joint_angle_deg != 0.0
    ) and limits.min_joint_angle_deg >= limits.max_joint_angle_deg:
        issues.append(
            ValidationIssue(
                "INVALID_LIMIT_RANGE",
                "limits",
                "configured minimum angle must be less than maximum angle",
            )
        )

    nonnegative = {
        "limits.max_motor_speed_rpm": limits.max_motor_speed_rpm,
        "limits.min_acceleration_time_ms": limits.min_acceleration_time_ms,
        "limits.min_deceleration_time_ms": limits.min_deceleration_time_ms,
        "limits.max_wait_time_ms": limits.max_wait_time_ms,
        "limits.max_cycle_count": limits.max_cycle_count,
        "limits.max_motor_temperature_c": limits.max_motor_temperature_c,
        "limits.max_encoder_temperature_c": limits.max_encoder_temperature_c,
        "limits.max_torque_percent": limits.max_torque_percent,
    }
    for path, number in nonnegative.items():
        if number < 0:
            issues.append(ValidationIssue("OUT_OF_RANGE", path, "must not be negative"))

    if config.serial.byteorder_32 != "unverified":
        issues.append(
            ValidationIssue(
                "BYTEORDER_MUST_REMAIN_UNVERIFIED",
                "serial.byteorder_32",
                "Milestone 1 must not select a 32-bit ordering",
            )
        )
    if not features.simulation:
        if not config.serial.device.startswith("/dev/serial/by-id/"):
            issues.append(
                ValidationIssue(
                    "NON_BY_ID_SERIAL_DEVICE",
                    "serial.device",
                    "real Pi configuration requires /dev/serial/by-id/...",
                )
            )
        issues.append(
            ValidationIssue(
                "REAL_HARDWARE_UNAVAILABLE",
                "features.simulation",
                "Milestone 1 supports simulation only",
            )
        )

    if not 1 <= config.motion_service.port <= 65535:
        issues.append(
            ValidationIssue("OUT_OF_RANGE", "motion_service.port", "must be 1 through 65535")
        )
    if not 1 <= config.monitoring_service.port <= 65535:
        issues.append(
            ValidationIssue(
                "OUT_OF_RANGE", "monitoring_service.port", "must be 1 through 65535"
            )
        )
    if config.motion_service.control_lease_ttl_s <= 0:
        issues.append(
            ValidationIssue(
                "OUT_OF_RANGE",
                "motion_service.control_lease_ttl_s",
                "must be greater than zero",
            )
        )

    if issues:
        raise ConfigValidationError(issues)
