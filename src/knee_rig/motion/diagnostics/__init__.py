"""Explicitly armed, one-shot Raspberry Pi read-only commissioning diagnostic."""

from knee_rig.motion.diagnostics.read_only import (
    READ_ONLY_REGISTERS,
    DiagnosticConfig,
    DiagnosticConfigError,
    DiagnosticErrorCode,
    DiagnosticResult,
    DIInterpretation,
    RegisterDefinition,
    crc16_modbus,
    load_diagnostic_config,
    plan_read,
    read_once,
)

__all__ = [
    "READ_ONLY_REGISTERS",
    "DIInterpretation",
    "DiagnosticConfig",
    "DiagnosticConfigError",
    "DiagnosticErrorCode",
    "DiagnosticResult",
    "RegisterDefinition",
    "crc16_modbus",
    "load_diagnostic_config",
    "plan_read",
    "read_once",
]
