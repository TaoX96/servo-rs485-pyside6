"""Bounded raw Modbus RTU read with no discovery, writes, retries, or polling."""

from __future__ import annotations

import importlib
import math
import sys
import time
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Protocol, cast


class DiagnosticErrorCode(StrEnum):
    CONFIG_INVALID = "CONFIG_INVALID"
    NOT_ARMED = "NOT_ARMED"
    PLATFORM_UNSUPPORTED = "PLATFORM_UNSUPPORTED"
    SERIAL_DEPENDENCY_UNAVAILABLE = "SERIAL_DEPENDENCY_UNAVAILABLE"
    SERIAL_OPEN_FAILED = "SERIAL_OPEN_FAILED"
    SERIAL_IO_FAILED = "SERIAL_IO_FAILED"
    SERIAL_WRITE_INCOMPLETE = "SERIAL_WRITE_INCOMPLETE"
    RESPONSE_TIMEOUT = "RESPONSE_TIMEOUT"
    RESPONSE_SHORT = "RESPONSE_SHORT"
    SLAVE_MISMATCH = "SLAVE_MISMATCH"
    FUNCTION_MISMATCH = "FUNCTION_MISMATCH"
    BYTE_COUNT_MISMATCH = "BYTE_COUNT_MISMATCH"
    CRC_MISMATCH = "CRC_MISMATCH"
    MODBUS_EXCEPTION = "MODBUS_EXCEPTION"
    PORT_CLOSE_FAILED = "PORT_CLOSE_FAILED"


@dataclass(frozen=True, slots=True)
class RegisterDefinition:
    symbol: str
    manual_label: str
    address: int
    function_code: int = 0x03
    word_count: int = 1


READ_ONLY_REGISTERS: Mapping[str, RegisterDefinition] = MappingProxyType(
    {
        definition.symbol: definition
        for definition in (
            RegisterDefinition("SERVO_STATUS", "U41.0A", 0x410A),
            RegisterDefinition("PLAN_OPERATION_GROUP", "U41.08", 0x4108),
            RegisterDefinition("DI_STATUS", "U40.04", 0x4004),
        )
    }
)


@dataclass(frozen=True, slots=True)
class DiagnosticConfig:
    device: str
    protocol: str
    slave_address: int
    baudrate: int
    data_bits: int
    parity: str
    stop_bits: int
    timeout_s: float
    pl_input_number: int = 0
    nl_input_number: int = 0
    pl_active_level: str = "unverified"
    nl_active_level: str = "unverified"


@dataclass(frozen=True, slots=True)
class DIInterpretation:
    input_number: int | None
    raw_level: str
    state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "input_number": self.input_number,
            "raw_level": self.raw_level,
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    ok: bool
    error_code: DiagnosticErrorCode | None
    message: str
    register: RegisterDefinition
    request_hex: str
    response_hex: str = ""
    request_utc: str | None = None
    response_utc: str | None = None
    request_monotonic_s: float | None = None
    response_monotonic_s: float | None = None
    elapsed_s: float | None = None
    request_crc: str | None = None
    response_crc_received: str | None = None
    response_crc_calculated: str | None = None
    response_crc_valid: bool | None = None
    modbus_exception_code: int | None = None
    raw_value: int | None = None
    interpretation: dict[str, object] | None = None
    port_closed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "error_code": self.error_code.value if self.error_code is not None else None,
            "message": self.message,
            "register": {
                "symbol": self.register.symbol,
                "manual_label": self.register.manual_label,
                "address_hex": f"0x{self.register.address:04X}",
                "function_code": self.register.function_code,
                "word_count": self.register.word_count,
            },
            "request_hex": self.request_hex,
            "response_hex": self.response_hex,
            "request_utc": self.request_utc,
            "response_utc": self.response_utc,
            "request_monotonic_s": self.request_monotonic_s,
            "response_monotonic_s": self.response_monotonic_s,
            "elapsed_s": self.elapsed_s,
            "crc": {
                "request": self.request_crc,
                "response_received": self.response_crc_received,
                "response_calculated": self.response_crc_calculated,
                "response_valid": self.response_crc_valid,
            },
            "modbus_exception_code": self.modbus_exception_code,
            "raw_value": self.raw_value,
            "interpretation": self.interpretation,
            "port_closed": self.port_closed,
        }


class DiagnosticConfigError(ValueError):
    """Configuration failed before any device was opened."""


class SerialPort(Protocol):
    def write(self, data: bytes) -> int: ...

    def flush(self) -> None: ...

    def read(self, size: int) -> bytes: ...

    def close(self) -> None: ...


SerialFactory = Callable[[DiagnosticConfig], SerialPort]
UtcClock = Callable[[], datetime]
MonotonicClock = Callable[[], float]


_SERIAL_KEYS = frozenset(
    {
        "device",
        "protocol",
        "slave_address",
        "baudrate",
        "data_bits",
        "parity",
        "stop_bits",
        "timeout_s",
        "pl_input_number",
        "nl_input_number",
        "pl_active_level",
        "nl_active_level",
        "byteorder_32",
        "legacy_byteorder_hypothesis",
    }
)
_REQUIRED_SERIAL_KEYS = frozenset(
    {
        "device",
        "protocol",
        "slave_address",
        "baudrate",
        "data_bits",
        "parity",
        "stop_bits",
        "timeout_s",
    }
)


def load_diagnostic_config(path: Path) -> DiagnosticConfig:
    """Load a reviewed local serial table without opening its configured device."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise DiagnosticConfigError(f"cannot read diagnostic configuration: {exc}") from exc
    serial = data.get("serial")
    if not isinstance(serial, dict):
        raise DiagnosticConfigError("a [serial] table is required")
    unknown = set(serial) - _SERIAL_KEYS
    missing = _REQUIRED_SERIAL_KEYS - set(serial)
    if unknown:
        raise DiagnosticConfigError(f"unknown [serial] fields: {sorted(unknown)}")
    if missing:
        raise DiagnosticConfigError(f"missing [serial] fields: {sorted(missing)}")
    try:
        config = DiagnosticConfig(
            device=_strict_str(serial, "device"),
            protocol=_strict_str(serial, "protocol"),
            slave_address=_strict_int(serial, "slave_address"),
            baudrate=_strict_int(serial, "baudrate"),
            data_bits=_strict_int(serial, "data_bits"),
            parity=_strict_str(serial, "parity"),
            stop_bits=_strict_int(serial, "stop_bits"),
            timeout_s=_strict_float(serial, "timeout_s"),
            pl_input_number=_optional_int(serial, "pl_input_number", 0),
            nl_input_number=_optional_int(serial, "nl_input_number", 0),
            pl_active_level=_optional_str(serial, "pl_active_level", "unverified"),
            nl_active_level=_optional_str(serial, "nl_active_level", "unverified"),
        )
    except (KeyError, TypeError) as exc:
        raise DiagnosticConfigError(str(exc)) from exc
    _validate_diagnostic_config(config)
    return config


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def plan_read(config: DiagnosticConfig, register: RegisterDefinition) -> DiagnosticResult:
    request = _request_frame(config, register)
    return DiagnosticResult(
        ok=True,
        error_code=None,
        message="Configuration valid; device was not opened.",
        register=register,
        request_hex=request.hex(" ").upper(),
        request_crc=request[-2:].hex(" ").upper(),
        port_closed=True,
    )


def read_once(
    config: DiagnosticConfig,
    register: RegisterDefinition,
    *,
    armed: bool,
    serial_factory: SerialFactory,
    utc_now: UtcClock = lambda: datetime.now(UTC),
    monotonic: MonotonicClock = time.monotonic,
) -> DiagnosticResult:
    """Open, send exactly one request, receive one bounded response, and close."""
    request = _request_frame(config, register)
    result = DiagnosticResult(
        ok=False,
        error_code=DiagnosticErrorCode.NOT_ARMED,
        message="The explicit --arm-read-only-hardware flag is required.",
        register=register,
        request_hex=request.hex(" ").upper(),
        request_crc=request[-2:].hex(" ").upper(),
    )
    if not armed:
        return result

    port: SerialPort
    try:
        port = serial_factory(config)
    except RuntimeError as exc:
        stable = {
            DiagnosticErrorCode.PLATFORM_UNSUPPORTED.value: DiagnosticErrorCode.PLATFORM_UNSUPPORTED,
            DiagnosticErrorCode.SERIAL_DEPENDENCY_UNAVAILABLE.value: (
                DiagnosticErrorCode.SERIAL_DEPENDENCY_UNAVAILABLE
            ),
        }.get(str(exc), DiagnosticErrorCode.SERIAL_OPEN_FAILED)
        return replace(result, error_code=stable, message="Serial device could not be opened.")
    except (OSError, ValueError):
        return replace(
            result,
            error_code=DiagnosticErrorCode.SERIAL_OPEN_FAILED,
            message="Serial device could not be opened.",
        )
    close_failed = False
    try:
        result = _exchange_once(
            port,
            request,
            result,
            config,
            utc_now,
            monotonic,
        )
    finally:
        try:
            port.close()
        except OSError:
            close_failed = True
    if close_failed:
        return replace(
            result,
            ok=False,
            error_code=DiagnosticErrorCode.PORT_CLOSE_FAILED,
            message="Serial port close failed.",
            port_closed=False,
        )
    return replace(result, port_closed=True)


def _exchange_once(
    port: SerialPort,
    request: bytes,
    result: DiagnosticResult,
    config: DiagnosticConfig,
    utc_now: UtcClock,
    monotonic: MonotonicClock,
) -> DiagnosticResult:
    request_utc = utc_now().isoformat()
    request_monotonic = monotonic()
    result = replace(
        result,
        request_utc=request_utc,
        request_monotonic_s=request_monotonic,
    )
    try:
        written = port.write(request)
        port.flush()
        if written != len(request):
            return replace(
                result,
                error_code=DiagnosticErrorCode.SERIAL_WRITE_INCOMPLETE,
                message="The single request frame was not written completely.",
            )
        header = port.read(3)
        if not header:
            return replace(
                result,
                error_code=DiagnosticErrorCode.RESPONSE_TIMEOUT,
                message="No response arrived before the bounded timeout.",
            )
        if len(header) < 3:
            return _with_response(
                result,
                header,
                DiagnosticErrorCode.RESPONSE_SHORT,
                "Response ended before its header was complete.",
                utc_now,
                monotonic,
            )
        expected_length = 5 if header[1] & 0x80 else 7
        remaining = expected_length - len(header)
        response = header + port.read(remaining)
    except (OSError, ValueError):
        return replace(
            result,
            error_code=DiagnosticErrorCode.SERIAL_IO_FAILED,
            message="Serial I/O failed during the single request.",
        )
    if len(response) < expected_length:
        return _with_response(
            result,
            response,
            DiagnosticErrorCode.RESPONSE_SHORT,
            "Response ended before the complete frame arrived.",
            utc_now,
            monotonic,
        )
    result = _with_response(result, response, None, "", utc_now, monotonic)
    return _validate_response(result, config)


def real_serial_factory(config: DiagnosticConfig) -> SerialPort:
    _require_raspberry_pi()
    try:
        serial = importlib.import_module("serial")
    except ImportError as exc:
        raise RuntimeError(DiagnosticErrorCode.SERIAL_DEPENDENCY_UNAVAILABLE.value) from exc
    parity = {"none": "N", "even": "E", "odd": "O"}[config.parity]
    raw_port = serial.Serial(
        port=config.device,
        baudrate=config.baudrate,
        bytesize=config.data_bits,
        parity=parity,
        stopbits=config.stop_bits,
        timeout=config.timeout_s,
        write_timeout=config.timeout_s,
        exclusive=True,
    )
    return cast(SerialPort, raw_port)


def _validate_response(result: DiagnosticResult, config: DiagnosticConfig) -> DiagnosticResult:
    response = bytes.fromhex(result.response_hex)
    if len(response) < 5:
        return replace(
            result,
            error_code=DiagnosticErrorCode.RESPONSE_SHORT,
            message="Response ended before CRC validation was possible.",
        )
    if not result.response_crc_valid:
        return replace(
            result,
            error_code=DiagnosticErrorCode.CRC_MISMATCH,
            message="Response CRC did not match the received frame.",
        )
    if response[0] != config.slave_address:
        return replace(
            result,
            error_code=DiagnosticErrorCode.SLAVE_MISMATCH,
            message="Response slave address did not match the request.",
        )
    if response[1] & 0x80:
        exception = response[2]
        return replace(
            result,
            error_code=DiagnosticErrorCode.MODBUS_EXCEPTION,
            message="The drive returned a Modbus exception.",
            modbus_exception_code=exception,
        )
    if response[1] != result.register.function_code:
        return replace(
            result,
            error_code=DiagnosticErrorCode.FUNCTION_MISMATCH,
            message="Response function code did not match FC03.",
        )
    if response[2] != 2 or len(response) != 7:
        return replace(
            result,
            error_code=DiagnosticErrorCode.BYTE_COUNT_MISMATCH,
            message="Response did not contain exactly one U16 word.",
        )
    raw_value = int.from_bytes(response[3:5], "big")
    interpretation = _interpret(result.register, raw_value, config)
    return replace(
        result,
        ok=True,
        error_code=None,
        message="One read-only U16 response was received and CRC-validated.",
        raw_value=raw_value,
        interpretation=interpretation,
    )


def _with_response(
    result: DiagnosticResult,
    response: bytes,
    error_code: DiagnosticErrorCode | None,
    message: str,
    utc_now: UtcClock,
    monotonic: MonotonicClock,
) -> DiagnosticResult:
    response_monotonic = monotonic()
    received_crc = calculated_crc = None
    crc_valid = None
    if len(response) >= 5:
        received = int.from_bytes(response[-2:], "little")
        calculated = crc16_modbus(response[:-2])
        received_crc = f"0x{received:04X}"
        calculated_crc = f"0x{calculated:04X}"
        crc_valid = received == calculated
    return replace(
        result,
        error_code=error_code,
        message=message,
        response_hex=response.hex(" ").upper(),
        response_utc=utc_now().isoformat(),
        response_monotonic_s=response_monotonic,
        elapsed_s=(
            response_monotonic - result.request_monotonic_s
            if result.request_monotonic_s is not None
            else None
        ),
        response_crc_received=received_crc,
        response_crc_calculated=calculated_crc,
        response_crc_valid=crc_valid,
    )


def _interpret(
    register: RegisterDefinition,
    raw_value: int,
    config: DiagnosticConfig,
) -> dict[str, object]:
    if register.symbol == "SERVO_STATUS":
        states = {0: "SERVO_NOT_READY", 1: "SERVO_READY", 2: "SERVO_RUNNING", 3: "FAULT"}
        return {"servo_status": states.get(raw_value, "UNDOCUMENTED_VALUE")}
    if register.symbol == "PLAN_OPERATION_GROUP":
        return {"planning_group": raw_value}
    bits = {f"DI{number}": bool(raw_value & (1 << (number - 1))) for number in range(1, 9)}
    return {
        "raw_input_levels": bits,
        "pl": _interpret_limit(raw_value, config.pl_input_number, config.pl_active_level).to_dict(),
        "nl": _interpret_limit(raw_value, config.nl_input_number, config.nl_active_level).to_dict(),
    }


def _interpret_limit(raw_value: int, input_number: int, active_level: str) -> DIInterpretation:
    if input_number == 0:
        return DIInterpretation(None, "UNMAPPED", "INPUT_ASSIGNMENT_UNVERIFIED")
    high = bool(raw_value & (1 << (input_number - 1)))
    raw_level = "HIGH" if high else "LOW"
    if active_level == "unverified":
        return DIInterpretation(input_number, raw_level, "ACTIVE_LEVEL_UNVERIFIED")
    active = high if active_level == "high" else not high
    return DIInterpretation(input_number, raw_level, "ACTIVE" if active else "INACTIVE")


def _request_frame(config: DiagnosticConfig, register: RegisterDefinition) -> bytes:
    body = bytes(
        (
            config.slave_address,
            register.function_code,
            register.address >> 8,
            register.address & 0xFF,
            0,
            register.word_count,
        )
    )
    return body + crc16_modbus(body).to_bytes(2, "little")


def _validate_diagnostic_config(config: DiagnosticConfig) -> None:
    path = PurePosixPath(config.device)
    if not config.device.startswith("/dev/serial/by-id/") or path.name in {"", ".", ".."}:
        raise DiagnosticConfigError("device must be an explicit /dev/serial/by-id/... path")
    if ".." in path.parts:
        raise DiagnosticConfigError("device path must not contain parent traversal")
    if config.protocol != "modbus_rtu":
        raise DiagnosticConfigError("protocol must be modbus_rtu")
    if not 1 <= config.slave_address <= 247:
        raise DiagnosticConfigError("slave_address must be 1 through 247")
    if config.baudrate <= 0 or config.data_bits != 8:
        raise DiagnosticConfigError("baudrate must be positive and data_bits must be 8")
    if config.parity not in {"none", "even", "odd"} or config.stop_bits not in {1, 2}:
        raise DiagnosticConfigError("parity or stop_bits is unsupported")
    if not math.isfinite(config.timeout_s) or not 0 < config.timeout_s <= 5:
        raise DiagnosticConfigError("timeout_s must be greater than zero and at most 5 seconds")
    if not 0 <= config.pl_input_number <= 8 or not 0 <= config.nl_input_number <= 8:
        raise DiagnosticConfigError("PL/NL input numbers must be 0 or DI1 through DI8")
    if config.pl_input_number and config.pl_input_number == config.nl_input_number:
        raise DiagnosticConfigError("PL and NL cannot use the same digital input")
    if config.pl_active_level not in {"unverified", "high", "low"}:
        raise DiagnosticConfigError("pl_active_level must be unverified, high, or low")
    if config.nl_active_level not in {"unverified", "high", "low"}:
        raise DiagnosticConfigError("nl_active_level must be unverified, high, or low")


def _require_raspberry_pi() -> None:
    if not sys.platform.startswith("linux"):
        raise RuntimeError(DiagnosticErrorCode.PLATFORM_UNSUPPORTED.value)
    model_path = Path("/proc/device-tree/model")
    try:
        model = model_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        raise RuntimeError(DiagnosticErrorCode.PLATFORM_UNSUPPORTED.value) from exc
    if "raspberry pi" not in model.lower():
        raise RuntimeError(DiagnosticErrorCode.PLATFORM_UNSUPPORTED.value)


def _strict_str(data: Mapping[str, object], key: str) -> str:
    value = data[key]
    if type(value) is not str:
        raise TypeError(f"serial.{key} must be a string")
    return value


def _strict_int(data: Mapping[str, object], key: str) -> int:
    value = data[key]
    if type(value) is not int:
        raise TypeError(f"serial.{key} must be an integer")
    return value


def _strict_float(data: Mapping[str, object], key: str) -> float:
    value = data[key]
    if type(value) not in {int, float}:
        raise TypeError(f"serial.{key} must be a number")
    return float(cast(int | float, value))


def _optional_str(data: Mapping[str, object], key: str, default: str) -> str:
    return _strict_str(data, key) if key in data else default


def _optional_int(data: Mapping[str, object], key: str, default: int) -> int:
    return _strict_int(data, key) if key in data else default
