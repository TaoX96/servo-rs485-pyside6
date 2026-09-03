"""Typed, layered configuration with fail-closed simulation defaults."""

from knee_rig.common.config.loader import ConfigValidationError, load_config
from knee_rig.common.config.models import (
    AppConfig,
    CalibrationConfig,
    FeatureConfig,
    HomingConfig,
    LimitsConfig,
    SerialConfig,
    default_config,
)

__all__ = [
    "AppConfig",
    "CalibrationConfig",
    "ConfigValidationError",
    "FeatureConfig",
    "HomingConfig",
    "LimitsConfig",
    "SerialConfig",
    "default_config",
    "load_config",
]
