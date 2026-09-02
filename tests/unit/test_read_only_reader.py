"""Symbolic, allowlisted fixture interpretation without physical-drive trust."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
from typing import cast

import pytest

from knee_rig.motion.driver import reader as reader_module
from knee_rig.motion.driver.codec import ByteOrder, CodecLayout, WordOrder
from knee_rig.motion.driver.fake_transport import FakeReadOnlyTransport, ReadCall, RecordedWords
from knee_rig.motion.driver.read_errors import (
    DecodeFailureError,
    ReadAuthorizationError,
    StaleResultError,
    UnknownSymbolError,
    UnresolvedAddressError,
    UnresolvedAreaError,
    UnverifiedLayoutError,
)
from knee_rig.motion.driver.read_models import LayoutVerification, ReadValidity
from knee_rig.motion.driver.reader import (
    ENGINEERING_READS,
    OPERATIONAL_READS,
    OfflineFixtureInterpretation,
    ReadOnlyServoReader,
)
from knee_rig.motion.driver.register_catalog import get_register
from knee_rig.motion.driver.register_spec import RegisterArea, VerificationStatus
from knee_rig.motion.simulation.clock import ManualClock

BIG = CodecLayout(ByteOrder.BIG)
BIG_HIGH = CodecLayout(ByteOrder.BIG, WordOrder.HIGH_WORD_FIRST)


def make_reader(
    symbol: str, words: tuple[object, ...], layout: CodecLayout = BIG, *, engineering: bool = False
) -> tuple[ReadOnlyServoReader, FakeReadOnlyTransport]:
    spec = get_register(symbol)
    assert spec.address is not None
    transport = FakeReadOnlyTransport(
        {
            ReadCall(
                RegisterArea.OFFLINE_FIXTURE, spec.address, spec.primitive.word_count
            ): RecordedWords(words)
        }
    )
    return ReadOnlyServoReader(
        transport,
        ManualClock(),
        engineering_read_permission=engineering,
        fixture_interpretation=OfflineFixtureInterpretation({symbol: layout}),
    ), transport


@pytest.mark.parametrize(
    ("symbol", "words", "layout", "scalar"),
    [
        ("SERVO_STATUS", (3,), BIG, 3),
        ("MOTOR_TEMPERATURE", (253,), BIG, 253),
        ("TORQUE_FEEDBACK", (0xFF85,), BIG, -123),
        ("TORQUE_FEEDBACK", (0x8000,), BIG, -32768),
        ("TORQUE_FEEDBACK", (0x7FFF,), BIG, 32767),
        ("BUS_VOLTAGE", (65535,), BIG, 65535),
        ("POSITION_FEEDBACK", (0x1234, 0x5678), BIG_HIGH, 0x12345678),
        ("POSITION_FEEDBACK", (0xFEDC, 0xBA99), BIG_HIGH, -0x1234567),
        ("POSITION_FEEDBACK", (0x8000, 0), BIG_HIGH, -2147483648),
        ("POSITION_FEEDBACK", (0x7FFF, 0xFFFF), BIG_HIGH, 2147483647),
    ],
)
def test_explicit_synthetic_decode_preserves_words_and_never_claims_hardware_trust(
    symbol: str, words: tuple[int, ...], layout: CodecLayout, scalar: int
) -> None:
    reader, transport = make_reader(symbol, words, layout)
    result = reader.read(symbol)
    assert result.scalar == scalar
    assert result.raw.words == words
    assert result.raw.sequence == 1
    assert result.raw.acquired_at == ManualClock().wall_time
    assert result.raw.catalog_area is RegisterArea.UNRESOLVED
    assert result.layout_verification is LayoutVerification.HARDWARE_UNVERIFIED
    assert result.validity is ReadValidity.FIXTURE_VALID
    assert transport.history[0].address == get_register(symbol).address
    assert transport.history[0].count == get_register(symbol).primitive.word_count
    with pytest.raises(FrozenInstanceError):
        result.scalar = 0


@pytest.mark.parametrize(
    ("layout", "words"),
    [
        (BIG_HIGH, (0x1234, 0x5678)),
        (CodecLayout(ByteOrder.LITTLE, WordOrder.HIGH_WORD_FIRST), (0x3412, 0x7856)),
        (CodecLayout(ByteOrder.BIG, WordOrder.LOW_WORD_FIRST), (0x5678, 0x1234)),
        (CodecLayout(ByteOrder.LITTLE, WordOrder.LOW_WORD_FIRST), (0x7856, 0x3412)),
    ],
)
def test_u32_engineering_fixture_under_every_explicit_layout(
    layout: CodecLayout, words: tuple[int, int]
) -> None:
    reader, _ = make_reader("GEAR_1_NUMERATOR", words, layout, engineering=True)
    assert reader.read("GEAR_1_NUMERATOR").scalar == 0x12345678


def test_allowlists_are_separate_immutable_and_engineering_disabled_by_default() -> None:
    assert isinstance(OPERATIONAL_READS, frozenset)
    assert isinstance(ENGINEERING_READS, frozenset)
    assert OPERATIONAL_READS.isdisjoint(ENGINEERING_READS)
    reader, transport = make_reader("GEAR_1_NUMERATOR", (1, 2), BIG_HIGH)
    with pytest.raises(ReadAuthorizationError):
        reader.read("GEAR_1_NUMERATOR")
    # Catalog membership does not grant reading: displacement belongs to neither list.
    with pytest.raises(ReadAuthorizationError):
        reader.read("GROUP_1_DISPLACEMENT")
    assert not transport.history
    assert not hasattr(reader, "write")


def test_unknown_and_numeric_symbols_cannot_bypass_lookup() -> None:
    reader, transport = make_reader("SERVO_STATUS", (1,))
    for symbol in ("UNKNOWN", "0x410A", 0x410A):
        with pytest.raises(UnknownSymbolError):
            reader.read(symbol)
    with pytest.raises(TypeError):
        reader.read("SERVO_STATUS", address=0)
    assert not transport.history


def test_unresolved_address_is_rejected_without_changing_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader, transport = make_reader("SERVO_STATUS", (1,))
    unresolved = replace(get_register("SERVO_STATUS"), address=None)
    monkeypatch.setattr(reader_module, "get_register", lambda symbol: unresolved)
    with pytest.raises(UnresolvedAddressError):
        reader.read("SERVO_STATUS")
    assert not transport.history


def test_default_area_and_missing_32_bit_layout_fail_closed() -> None:
    transport = FakeReadOnlyTransport({})
    reader = ReadOnlyServoReader(transport, ManualClock())
    with pytest.raises(UnresolvedAreaError):
        reader.read("SERVO_STATUS")
    reader = ReadOnlyServoReader(
        transport, ManualClock(), fixture_interpretation=OfflineFixtureInterpretation({})
    )
    with pytest.raises(UnverifiedLayoutError):
        reader.read("POSITION_FEEDBACK")
    assert not transport.history


def test_layouts_are_defensively_copied_and_codec_error_is_local() -> None:
    layouts = {"SERVO_STATUS": BIG_HIGH}  # Invalid for a U16, deliberately.
    interpretation = OfflineFixtureInterpretation(layouts)
    layouts.clear()
    assert interpretation.layouts["SERVO_STATUS"] == BIG_HIGH
    reader, transport = make_reader("SERVO_STATUS", (1,), BIG_HIGH)
    with pytest.raises(DecodeFailureError) as failure:
        reader.read("SERVO_STATUS")
    assert failure.value.code == "DECODE_FAILURE"
    assert len(transport.history) == 1


def test_scale_metadata_application_units_and_ambiguous_speed() -> None:
    reader, _ = make_reader("MOTOR_TEMPERATURE", (253,))
    result = reader.read("MOTOR_TEMPERATURE")
    assert result.scalar == 253
    assert result.scale == Fraction(1, 10)
    assert result.unit == "deg_C"
    reader, _ = make_reader("POSITION_FEEDBACK", (0, 42), BIG_HIGH)
    assert reader.read("POSITION_FEEDBACK").unit == "application_unit"
    reader, _ = make_reader("SPEED_FEEDBACK", (0xFFFE,))
    result = reader.read("SPEED_FEEDBACK")
    assert result.scalar is None
    assert result.raw.words == (0xFFFE,)
    assert result.validity is ReadValidity.AMBIGUOUS
    assert result.documentary_verification is VerificationStatus.AMBIGUOUS
    assert result.ambiguity
    assert result.layout is None


@pytest.mark.parametrize(("words", "scalar"), [((0, 0), 0), ((0xFFFF, 0xFFFF), 4294967295)])
def test_u32_boundary_fixtures(words: tuple[int, int], scalar: int) -> None:
    reader, _ = make_reader("GEAR_1_NUMERATOR", words, BIG_HIGH, engineering=True)
    assert reader.read("GEAR_1_NUMERATOR").scalar == scalar


def test_override_mapping_is_immutable_and_permission_is_strict() -> None:
    interpretation = OfflineFixtureInterpretation({"SERVO_STATUS": BIG})
    with pytest.raises(TypeError):
        cast(dict[str, CodecLayout], interpretation.layouts)["SERVO_STATUS"] = BIG_HIGH
    with pytest.raises(ReadAuthorizationError):
        ReadOnlyServoReader(
            FakeReadOnlyTransport({}), ManualClock(), engineering_read_permission=cast(bool, "true")
        )
    assert all(
        get_register(symbol).area is RegisterArea.UNRESOLVED
        for symbol in OPERATIONAL_READS | ENGINEERING_READS
    )


def test_success_is_not_cached_after_a_stale_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    reader, transport = make_reader("SERVO_STATUS", (1,))
    assert reader.read("SERVO_STATUS").raw.fresh_at_acquisition

    def stale(area: RegisterArea, address: int, count: int) -> tuple[int, ...]:
        raise StaleResultError("synthetic stale failure")

    monkeypatch.setattr(transport, "read_words", stale)
    with pytest.raises(StaleResultError):
        reader.read("SERVO_STATUS")
    snapshot = reader.snapshot(("SERVO_STATUS",))
    assert snapshot.fields[0].result is None
    assert snapshot.fields[0].failure.code == "STALE_RESULT"
