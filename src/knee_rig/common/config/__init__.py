"""Typed, layered configuration with fail-closed simulation defaults."""

from knee_rig.common.config.loader import ConfigValidationError, load_config
from knee_rig.common.config.models import (
    AppConfig,
    CalibrationConfig,
    FeatureConfig,
    LimitsConfig,
    SerialConfig,
    default_config,
)

__all__ = [
    "AppConfig",
    "CalibrationConfig",
    "ConfigValidationError",
    "FeatureConfig",
    "LimitsConfig",
    "SerialConfig",
    "default_config",
    "load_config",
]
