"""One-shot offline assembly, with explicit partial failures and deterministic time."""

from __future__ import annotations

import pytest

from knee_rig.motion.driver.codec import ByteOrder, CodecLayout, WordOrder
from knee_rig.motion.driver.fake_transport import (
    FakeReadOnlyTransport,
    FixtureFailure,
    ReadCall,
    RecordedWords,
)
from knee_rig.motion.driver.read_errors import ReadAuthorizationError
from knee_rig.motion.driver.read_models import ReadValidity
from knee_rig.motion.driver.reader import (
    DEFAULT_SNAPSHOT,
    OfflineFixtureInterpretation,
    ReadOnlyServoReader,
)
from knee_rig.motion.driver.register_spec import RegisterArea
from knee_rig.motion.driver.transport import ReadSource
from knee_rig.motion.simulation.clock import ManualClock


def test_complete_synthetic_snapshot_and_injected_time() -> None:
    clock = ManualClock()
    transport = FakeReadOnlyTransport(
        {
            ReadCall(RegisterArea.OFFLINE_FIXTURE, 0x410A, 1): RecordedWords((1,)),
            ReadCall(RegisterArea.OFFLINE_FIXTURE, 0x4003, 1): RecordedWords((0xFF85,)),
        }
    )
    reader = ReadOnlyServoReader(
        transport,
        clock,
        fixture_interpretation=OfflineFixtureInterpretation(
            {
                "SERVO_STATUS": CodecLayout(ByteOrder.BIG),
                "TORQUE_FEEDBACK": CodecLayout(ByteOrder.BIG),
            }
        ),
    )
    first = reader.snapshot(("SERVO_STATUS", "TORQUE_FEEDBACK"))
    assert first.validity is ReadValidity.FIXTURE_VALID
    assert first.source is ReadSource.SYNTHETIC_FIXTURE
    assert [field.result.scalar for field in first.fields] == [1, -123]
    assert all(field.failure is None for field in first.fields)
    clock.advance(2)
    second = reader.snapshot(("SERVO_STATUS", "TORQUE_FEEDBACK"))
    assert second.sequence == first.sequence + 1
    assert second.monotonic_s == 2
    assert second.acquired_at == clock.wall_time
    assert [field.result.raw.sequence for field in second.fields] == [3, 4]
    assert len(transport.history) == 4


@pytest.mark.parametrize("failure", [FixtureFailure.TIMEOUT, FixtureFailure.STALE])
def test_partial_transport_failure_has_no_zero_or_stale_substitution(
    failure: FixtureFailure,
) -> None:
    transport = FakeReadOnlyTransport(
        {
            ReadCall(RegisterArea.OFFLINE_FIXTURE, 0x410A, 1): RecordedWords((1,)),
            ReadCall(RegisterArea.OFFLINE_FIXTURE, 0x4003, 1): RecordedWords(failure=failure),
        }
    )
    reader = ReadOnlyServoReader(
        transport,
        ManualClock(),
        fixture_interpretation=OfflineFixtureInterpretation(
            {
                "SERVO_STATUS": CodecLayout(ByteOrder.BIG),
                "TORQUE_FEEDBACK": CodecLayout(ByteOrder.BIG),
            }
        ),
    )
    result = reader.snapshot(("SERVO_STATUS", "TORQUE_FEEDBACK"))
    assert result.validity is ReadValidity.DEGRADED
    assert result.fields[0].result.scalar == 1
    assert result.fields[1].result is None
    assert result.fields[1].failure.code == (
        "TRANSPORT_TIMEOUT" if failure is FixtureFailure.TIMEOUT else "STALE_RESULT"
    )
    assert len(transport.history) == 2


def test_partial_decode_failure_is_not_a_communication_error() -> None:
    transport = FakeReadOnlyTransport(
        {
            ReadCall(RegisterArea.OFFLINE_FIXTURE, 0x410A, 1): RecordedWords((1,)),
        }
    )
    reader = ReadOnlyServoReader(
        transport,
        ManualClock(),
        fixture_interpretation=OfflineFixtureInterpretation(
            {
                "SERVO_STATUS": CodecLayout(ByteOrder.BIG, WordOrder.HIGH_WORD_FIRST),
            }
        ),
    )
    result = reader.snapshot(("SERVO_STATUS",))
    assert result.validity is ReadValidity.DEGRADED
    assert result.fields[0].result is None
    assert result.fields[0].failure.code == "DECODE_FAILURE"
    assert len(transport.history) == 1


def test_ambiguous_speed_degrades_snapshot_without_inventing_decoded_value() -> None:
    transport = FakeReadOnlyTransport(
        {
            ReadCall(RegisterArea.OFFLINE_FIXTURE, 0x4001, 1): RecordedWords((123,)),
        }
    )
    reader = ReadOnlyServoReader(
        transport, ManualClock(), fixture_interpretation=OfflineFixtureInterpretation({})
    )
    result = reader.snapshot(("SPEED_FEEDBACK",))
    assert result.validity is ReadValidity.DEGRADED
    assert result.fields[0].result.raw.words == (123,)
    assert result.fields[0].result.scalar is None


def test_snapshot_rejects_engineering_even_when_permission_enabled() -> None:
    reader = ReadOnlyServoReader(
        FakeReadOnlyTransport({}), ManualClock(), engineering_read_permission=True
    )
    with pytest.raises(ReadAuthorizationError):
        reader.snapshot(("GEAR_1_NUMERATOR",))


def test_all_default_fields_preserve_synthetic_records_and_speed_ambiguity() -> None:
    # Explicit synthetic words; none were captured from a drive or encoded by production code.
    rows = (
        ("SERVO_STATUS", 0x410A, (1,)),
        ("POSITION_FEEDBACK", 0x4016, (0xFEDC, 0xBA99)),
        ("SPEED_FEEDBACK", 0x4001, (0xFFFE,)),
        ("TORQUE_FEEDBACK", 0x4003, (0xFF85,)),
        ("DI_STATUS", 0x4004, (0x00FE,)),
        ("BUS_VOLTAGE", 0x4006, (2300,)),
        ("POSITION_DEVIATION", 0x4010, (0, 7)),
        ("MOTOR_TEMPERATURE", 0x4031, (253,)),
        ("ENCODER_TEMPERATURE", 0x4032, (251,)),
        ("PLAN_OPERATION_GROUP", 0x4108, (2,)),
    )
    fixtures = {
        ReadCall(RegisterArea.OFFLINE_FIXTURE, address, len(words)): RecordedWords(words)
        for _, address, words in rows
    }
    layouts = {
        symbol: CodecLayout(ByteOrder.BIG, WordOrder.HIGH_WORD_FIRST if len(words) == 2 else None)
        for symbol, _, words in rows
    }
    transport = FakeReadOnlyTransport(fixtures)
    reader = ReadOnlyServoReader(
        transport, ManualClock(), fixture_interpretation=OfflineFixtureInterpretation(layouts)
    )
    snapshot = reader.snapshot()
    assert tuple(field.symbol for field in snapshot.fields) == DEFAULT_SNAPSHOT
    assert snapshot.validity is ReadValidity.DEGRADED
    assert len(transport.history) == 10
    expected_words = {symbol: words for symbol, _, words in rows}
    for field in snapshot.fields:
        assert field.failure is None
        assert field.result.raw.words == expected_words[field.symbol]
        assert field.result.raw.fresh_at_acquisition
        assert field.result.validity is (
            ReadValidity.AMBIGUOUS
            if field.symbol == "SPEED_FEEDBACK"
            else ReadValidity.FIXTURE_VALID
        )
