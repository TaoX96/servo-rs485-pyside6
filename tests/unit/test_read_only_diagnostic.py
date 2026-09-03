"""The laboratory diagnostic performs exactly one bounded symbolic read and closes."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from knee_rig.motion.diagnostics.__main__ import build_parser
from knee_rig.motion.diagnostics.read_only import (
    READ_ONLY_REGISTERS,
    DiagnosticConfig,
    DiagnosticConfigError,
    DiagnosticErrorCode,
    crc16_modbus,
    load_diagnostic_config,
    plan_read,
    read_once,
)


@dataclass
class FakePort:
    chunks: list[bytes]
    written: list[bytes] = field(default_factory=list)
    closed: bool = False
    fail_write: bool = False
    short_write: bool = False
    fail_close: bool = False

    def write(self, data: bytes) -> int:
        if self.fail_write:
            raise OSError("synthetic write failure")
        self.written.append(data)
        return len(data) - 1 if self.short_write else len(data)

    def flush(self) -> None:
        return None

    def read(self, size: int) -> bytes:
        del size
        return self.chunks.pop(0) if self.chunks else b""

    def close(self) -> None:
        self.closed = True
        if self.fail_close:
            raise OSError("synthetic close failure")


def _config(**changes: object) -> DiagnosticConfig:
    values: dict[str, object] = {
        "device": "/dev/serial/by-id/usb-reviewed-adapter",
        "protocol": "modbus_rtu",
        "slave_address": 1,
        "baudrate": 9600,
        "data_bits": 8,
        "parity": "none",
        "stop_bits": 1,
        "timeout_s": 1.0,
        "pl_input_number": 1,
        "nl_input_number": 2,
        "pl_active_level": "unverified",
        "nl_active_level": "low",
    }
    values.update(changes)
    return DiagnosticConfig(**values)  # type: ignore[arg-type]


def _frame(function: int = 3, data: bytes = b"\x02\x00\x01", slave: int = 1) -> bytes:
    body = bytes((slave, function)) + data
    return body + crc16_modbus(body).to_bytes(2, "little")


def _clock(values: tuple[float, ...] = (10.0, 10.25)) -> Iterator[float]:
    yield from values


def _run(port: FakePort, *, symbol: str = "SERVO_STATUS"):
    times = _clock()
    return read_once(
        _config(),
        READ_ONLY_REGISTERS[symbol],
        armed=True,
        serial_factory=lambda config: port,
        monotonic=lambda: next(times),
    )


def test_allowlist_contains_only_documented_symbolic_u16_reads() -> None:
    assert tuple(READ_ONLY_REGISTERS) == (
        "SERVO_STATUS",
        "PLAN_OPERATION_GROUP",
        "DI_STATUS",
    )
    assert all(
        item.function_code == 3 and item.word_count == 1 for item in READ_ONLY_REGISTERS.values()
    )
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["read", "--config", "pi.local.toml", "--register", "0x410A"])


def test_config_preview_builds_exact_frame_without_opening() -> None:
    result = plan_read(_config(), READ_ONLY_REGISTERS["SERVO_STATUS"])
    assert result.ok
    assert result.request_hex == "01 03 41 0A 00 01 B0 34"
    assert result.port_closed
    assert result.request_utc is None


def test_unarmed_read_never_opens_port() -> None:
    opened = False

    def factory(config: DiagnosticConfig) -> FakePort:
        nonlocal opened
        opened = True
        return FakePort([])

    result = read_once(
        _config(),
        READ_ONLY_REGISTERS["SERVO_STATUS"],
        armed=False,
        serial_factory=factory,
    )
    assert result.error_code is DiagnosticErrorCode.NOT_ARMED
    assert not opened


def test_success_captures_raw_frames_timestamps_crc_and_closes() -> None:
    response = _frame()
    port = FakePort([response[:3], response[3:]])
    result = _run(port)
    assert result.ok
    assert result.raw_value == 1
    assert result.interpretation == {"servo_status": "SERVO_READY"}
    assert result.response_crc_valid
    assert result.elapsed_s == 0.25
    assert len(port.written) == 1
    assert port.closed and result.port_closed


def test_di_status_preserves_raw_bits_and_unverified_polarity() -> None:
    response = _frame(data=b"\x02\x00\x01")
    result = _run(FakePort([response[:3], response[3:]]), symbol="DI_STATUS")
    assert result.raw_value == 1
    assert result.interpretation is not None
    assert result.interpretation["raw_input_levels"]["DI1"] is True  # type: ignore[index]
    assert result.interpretation["pl"]["state"] == "ACTIVE_LEVEL_UNVERIFIED"  # type: ignore[index]
    assert result.interpretation["nl"]["state"] == "ACTIVE"  # type: ignore[index]


@pytest.mark.parametrize(
    ("port", "expected"),
    [
        (FakePort([]), DiagnosticErrorCode.RESPONSE_TIMEOUT),
        (FakePort([b"\x01\x03"]), DiagnosticErrorCode.RESPONSE_SHORT),
        (FakePort([], fail_write=True), DiagnosticErrorCode.SERIAL_IO_FAILED),
        (FakePort([], short_write=True), DiagnosticErrorCode.SERIAL_WRITE_INCOMPLETE),
    ],
)
def test_io_errors_are_stable_and_close(port: FakePort, expected: DiagnosticErrorCode) -> None:
    result = _run(port)
    assert result.error_code is expected
    assert port.closed and result.port_closed
    assert len(port.written) <= 1


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (_frame(slave=2), DiagnosticErrorCode.SLAVE_MISMATCH),
        (_frame(function=4), DiagnosticErrorCode.FUNCTION_MISMATCH),
        (_frame(data=b"\x04\x00\x01"), DiagnosticErrorCode.BYTE_COUNT_MISMATCH),
        (_frame(function=0x83, data=b"\x02"), DiagnosticErrorCode.MODBUS_EXCEPTION),
    ],
)
def test_protocol_errors_are_stable_and_close(
    response: bytes, expected: DiagnosticErrorCode
) -> None:
    result = _run(FakePort([response[:3], response[3:]]))
    assert result.error_code is expected
    assert result.port_closed


def test_crc_mismatch_is_reported_and_port_closes() -> None:
    response = bytearray(_frame())
    response[-1] ^= 0xFF
    result = _run(FakePort([bytes(response[:3]), bytes(response[3:])]))
    assert result.error_code is DiagnosticErrorCode.CRC_MISMATCH
    assert result.response_crc_valid is False
    assert result.port_closed


def test_partial_body_is_captured_as_short_response_and_port_closes() -> None:
    result = _run(FakePort([b"\x01\x03\x02", b"\x00"]))
    assert result.error_code is DiagnosticErrorCode.RESPONSE_SHORT
    assert result.response_hex == "01 03 02 00"
    assert result.port_closed


def test_open_and_close_failures_have_distinct_codes() -> None:
    opened = read_once(
        _config(),
        READ_ONLY_REGISTERS["SERVO_STATUS"],
        armed=True,
        serial_factory=lambda config: (_ for _ in ()).throw(OSError("synthetic")),
    )
    assert opened.error_code is DiagnosticErrorCode.SERIAL_OPEN_FAILED
    port = FakePort([], fail_close=True)
    closed = _run(port)
    assert closed.error_code is DiagnosticErrorCode.PORT_CLOSE_FAILED
    assert not closed.port_closed


def test_local_config_requires_explicit_by_id_path_and_complete_serial_values(
    tmp_path: Path,
) -> None:
    path = tmp_path / "pi.local.toml"
    path.write_text(
        """[serial]
device = "/dev/ttyUSB0"
protocol = "modbus_rtu"
slave_address = 1
baudrate = 9600
data_bits = 8
parity = "none"
stop_bits = 1
timeout_s = 1.0
""",
        encoding="utf-8",
    )
    with pytest.raises(DiagnosticConfigError, match="/dev/serial/by-id"):
        load_diagnostic_config(path)
