"""Golden-vector and rejection coverage for the pure register codec."""

from __future__ import annotations

from typing import cast

import pytest

from knee_rig.motion.driver import (
    ByteOrder,
    CodecConfigurationError,
    CodecLayout,
    PrimitiveType,
    RegisterWordError,
    UnsupportedPrimitiveTypeError,
    ValueOutOfRangeError,
    WordCountMismatchError,
    WordOrder,
    decode_scalar,
    encode_scalar,
)

BIG_16 = CodecLayout(ByteOrder.BIG)
LITTLE_16 = CodecLayout(ByteOrder.LITTLE)
LAYOUTS_32 = (
    CodecLayout(ByteOrder.BIG, WordOrder.HIGH_WORD_FIRST),
    CodecLayout(ByteOrder.LITTLE, WordOrder.HIGH_WORD_FIRST),
    CodecLayout(ByteOrder.BIG, WordOrder.LOW_WORD_FIRST),
    CodecLayout(ByteOrder.LITTLE, WordOrder.LOW_WORD_FIRST),
)


@pytest.mark.parametrize(
    ("layout", "expected"),
    (
        (LAYOUTS_32[0], (0x1234, 0x5678)),
        (LAYOUTS_32[1], (0x3412, 0x7856)),
        (LAYOUTS_32[2], (0x5678, 0x1234)),
        (LAYOUTS_32[3], (0x7856, 0x3412)),
    ),
)
def test_u32_golden_vector_for_every_layout(layout: CodecLayout, expected: tuple[int, int]) -> None:
    assert encode_scalar(0x12345678, PrimitiveType.U32, layout) == expected
    assert decode_scalar(expected, PrimitiveType.U32, layout) == 0x12345678


def test_16_bit_golden_vectors_and_twos_complement() -> None:
    assert encode_scalar(0x1234, PrimitiveType.U16, BIG_16) == (0x1234,)
    assert encode_scalar(0x1234, PrimitiveType.U16, LITTLE_16) == (0x3412,)
    assert encode_scalar(-1, PrimitiveType.I16, BIG_16) == (0xFFFF,)
    assert decode_scalar((0x8000,), PrimitiveType.I16, BIG_16) == -32768


def test_signed_32_bit_non_symmetric_golden_vector() -> None:
    assert encode_scalar(-0x1234567, PrimitiveType.I32, LAYOUTS_32[0]) == (0xFEDC, 0xBA99)
    assert decode_scalar((0xFEDC, 0xBA99), PrimitiveType.I32, LAYOUTS_32[0]) == -0x1234567


@pytest.mark.parametrize(
    ("primitive", "values"),
    (
        (PrimitiveType.U16, (0, 1, 0x1234, 65535)),
        (PrimitiveType.I16, (-32768, -1, 0, 0x1234, 32767)),
        (PrimitiveType.U32, (0, 1, 0x12345678, 4294967295)),
        (PrimitiveType.I32, (-2147483648, -0x1234567, -1, 0, 0x12345678, 2147483647)),
    ),
)
def test_boundary_and_interior_round_trips(
    primitive: PrimitiveType, values: tuple[int, ...]
) -> None:
    layouts = (BIG_16, LITTLE_16) if primitive.word_count == 1 else LAYOUTS_32
    for layout in layouts:
        for value in values:
            assert (
                decode_scalar(encode_scalar(value, primitive, layout), primitive, layout) == value
            )


@pytest.mark.parametrize(
    ("primitive", "value"),
    (
        (PrimitiveType.U16, -1),
        (PrimitiveType.U16, 65536),
        (PrimitiveType.I16, -32769),
        (PrimitiveType.I16, 32768),
        (PrimitiveType.U32, -1),
        (PrimitiveType.U32, 4294967296),
        (PrimitiveType.I32, -2147483649),
        (PrimitiveType.I32, 2147483648),
    ),
)
def test_out_of_range_values_are_rejected(primitive: PrimitiveType, value: int) -> None:
    layout = BIG_16 if primitive.word_count == 1 else LAYOUTS_32[0]
    with pytest.raises(ValueOutOfRangeError):
        encode_scalar(value, primitive, layout)


@pytest.mark.parametrize("value", (1.0, "1", True, None))
def test_non_integer_source_values_are_rejected(value: object) -> None:
    with pytest.raises(ValueOutOfRangeError):
        encode_scalar(value, PrimitiveType.U16, BIG_16)


@pytest.mark.parametrize("words", ((-1,), (65536,), (True,), (1.0,), ("1",)))
def test_invalid_register_words_are_rejected(words: tuple[object, ...]) -> None:
    with pytest.raises(RegisterWordError):
        decode_scalar(words, PrimitiveType.U16, BIG_16)


@pytest.mark.parametrize("words", ((), (1, 2), (1, 2, 3)))
def test_wrong_word_counts_are_rejected(words: tuple[int, ...]) -> None:
    with pytest.raises(WordCountMismatchError):
        decode_scalar(words, PrimitiveType.U16, BIG_16)


@pytest.mark.parametrize("words", ("1234", b"12", {1}, None, 1))
def test_malformed_word_sequences_are_rejected(words: object) -> None:
    with pytest.raises(RegisterWordError):
        decode_scalar(words, PrimitiveType.U16, BIG_16)


def test_layout_and_primitive_must_be_explicit_and_valid() -> None:
    with pytest.raises(CodecConfigurationError):
        encode_scalar(1, PrimitiveType.U32, None)
    with pytest.raises(CodecConfigurationError):
        encode_scalar(1, PrimitiveType.U32, CodecLayout(ByteOrder.BIG))
    with pytest.raises(CodecConfigurationError):
        encode_scalar(1, PrimitiveType.U16, LAYOUTS_32[0])
    with pytest.raises(CodecConfigurationError):
        CodecLayout(cast(ByteOrder, "big"))
    with pytest.raises(CodecConfigurationError):
        CodecLayout(ByteOrder.BIG, cast(WordOrder, "high"))
    with pytest.raises(UnsupportedPrimitiveTypeError):
        encode_scalar(1, "U16", BIG_16)
