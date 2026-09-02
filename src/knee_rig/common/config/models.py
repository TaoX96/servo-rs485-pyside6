"""Configuration models whose defaults cannot authorize real hardware."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FeatureConfig:
    simulation: bool = True
    allow_servo_enable: bool = False
    allow_motion: bool = False
    allow_homing: bool = False
    allow_persistent_parameter_write: bool = False
    calibration_verified: bool = False


@dataclass(frozen=True, slots=True)
class CalibrationConfig:
    position_units_per_joint_degree: float = 0.0
    joint_zero_offset_deg: float = 0.0
    direction_sign: int = 0

    def position_units_for_angle(self, joint_angle_deg: float) -> float:
        """Convert an angle only after the caller has verified calibration."""
        angle = Decimal(str(joint_angle_deg))
        zero = Decimal(str(self.joint_zero_offset_deg))
        factor = Decimal(str(self.position_units_per_joint_degree))
        return float((angle - zero) * factor * self.direction_sign)


@dataclass(frozen=True, slots=True)
class LimitsConfig:
    min_joint_angle_deg: float = 0.0
    max_joint_angle_deg: float = 0.0
    max_motor_speed_rpm: int = 0
    min_acceleration_time_ms: int = 0
    min_deceleration_time_ms: int = 0
    max_wait_time_ms: int = 0
    max_cycle_count: int = 0
    max_motor_temperature_c: float = 0.0
    max_encoder_temperature_c: float = 0.0
    max_torque_percent: float = 0.0


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    level: str = "INFO"
    directory: str = ""


@dataclass(frozen=True, slots=True)
class MotionServiceConfig:
    bind_host: str = "127.0.0.1"
    port: int = 8765
    control_lease_ttl_s: float = 5.0


@dataclass(frozen=True, slots=True)
class SerialConfig:
    device: str = ""
    protocol: str = "modbus_rtu"
    slave_address: int = 1
    baudrate: int = 9600
    data_bits: int = 8
    parity: str = "none"
    stop_bits: int = 1
    timeout_s: float = 1.0
    byteorder_32: str = "unverified"
    legacy_byteorder_hypothesis: str = "little"


@dataclass(frozen=True, slots=True)
class MonitoringServiceConfig:
    bind_host: str = "127.0.0.1"
    port: int = 8766
    allow_camera: bool = False
    allow_recording: bool = False
    allow_temperature_sensor: bool = False
    media_directory: str = ""


@dataclass(frozen=True, slots=True)
class EndpointConfig:
    base_url: str = ""
    request_timeout_s: float = 3.0


@dataclass(frozen=True, slots=True)
class MotionApiConfig:
    base_url: str = "http://127.0.0.1:8765"
    request_timeout_s: float = 3.0
    lease_renewal_interval_s: float = 1.0


@dataclass(frozen=True, slots=True)
class MonitoringApiConfig:
    base_url: str = "http://127.0.0.1:8766"
    request_timeout_s: float = 3.0
    temperature_interval_s: float = 5.0


@dataclass(frozen=True, slots=True)
class GuiConfig:
    start_maximized: bool = False
    confirm_state_changing_commands: bool = True


@dataclass(frozen=True, slots=True)
class AppConfig:
    features: FeatureConfig = FeatureConfig()
    calibration: CalibrationConfig = CalibrationConfig()
    limits: LimitsConfig = LimitsConfig()
    logging: LoggingConfig = LoggingConfig()
    motion_service: MotionServiceConfig = MotionServiceConfig()
    serial: SerialConfig = SerialConfig()
    monitoring_service: MonitoringServiceConfig = MonitoringServiceConfig()
    motion_api: MotionApiConfig = MotionApiConfig()
    monitoring_api: MonitoringApiConfig = MonitoringApiConfig()
    gui: GuiConfig = GuiConfig()


def default_config() -> AppConfig:
    """Return a new immutable configuration with simulation-only safe defaults."""
    return AppConfig()
