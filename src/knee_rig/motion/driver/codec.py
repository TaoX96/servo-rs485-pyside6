"""Pure register-word encoding and decoding with no transport assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class RegisterCodecError(ValueError):
    """Base class for deterministic local codec failures."""


class CodecConfigurationError(RegisterCodecError):
    """The requested byte/word layout is missing or invalid."""


class ValueOutOfRangeError(RegisterCodecError):
    """A source scalar cannot be represented by its primitive type."""


class RegisterWordError(RegisterCodecError):
    """A register word is not a strict unsigned 16-bit integer."""


class WordCountMismatchError(RegisterCodecError):
    """The number of supplied words does not match the primitive type."""


class UnsupportedPrimitiveTypeError(RegisterCodecError):
    """The supplied primitive type is not supported."""


class PrimitiveType(StrEnum):
    U16 = "U16"
    I16 = "I16"
    U32 = "U32"
    I32 = "I32"

    @property
    def bits(self) -> int:
        return 16 if self in {PrimitiveType.U16, PrimitiveType.I16} else 32

    @property
    def signed(self) -> bool:
        return self in {PrimitiveType.I16, PrimitiveType.I32}

    @property
    def word_count(self) -> int:
        return self.bits // 16

    @property
    def minimum(self) -> int:
        return -(1 << (self.bits - 1)) if self.signed else 0

    @property
    def maximum(self) -> int:
        return (1 << (self.bits - 1)) - 1 if self.signed else (1 << self.bits) - 1


class ByteOrder(StrEnum):
    BIG = "big"
    LITTLE = "little"


class WordOrder(StrEnum):
    HIGH_WORD_FIRST = "high_word_first"
    LOW_WORD_FIRST = "low_word_first"


@dataclass(frozen=True, slots=True)
class CodecLayout:
    """Explicit layout required for every conversion."""

    byte_order: ByteOrder
    word_order: WordOrder | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.byte_order, ByteOrder):
            raise CodecConfigurationError("byte_order must be a ByteOrder")
        if self.word_order is not None and not isinstance(self.word_order, WordOrder):
            raise CodecConfigurationError("word_order must be a WordOrder or None")


_WORD_MAX: Final = 0xFFFF


def encode_scalar(value: object, primitive: object, layout: CodecLayout | None) -> tuple[int, ...]:
    """Encode a strict integer scalar into transport-independent 16-bit words."""
    kind = _validate_primitive(primitive)
    selected = _validate_layout(kind, layout)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueOutOfRangeError(f"{kind.value} source must be an integer, not bool")
    if not kind.minimum <= value <= kind.maximum:
        raise ValueOutOfRangeError(
            f"{kind.value} value {value} is outside [{kind.minimum}, {kind.maximum}]"
        )
    raw = value & ((1 << kind.bits) - 1)
    words = [raw & _WORD_MAX] if kind.word_count == 1 else [raw >> 16, raw & _WORD_MAX]
    words = [_apply_byte_order(word, selected.byte_order) for word in words]
    if kind.word_count == 2 and selected.word_order is WordOrder.LOW_WORD_FIRST:
        words.reverse()
    return tuple(words)


def decode_scalar(words: object, primitive: object, layout: CodecLayout | None) -> int:
    """Decode an exact register-word sequence into a typed Python integer."""
    kind = _validate_primitive(primitive)
    selected = _validate_layout(kind, layout)
    if isinstance(words, (str, bytes, bytearray)) or not isinstance(words, (list, tuple)):
        raise RegisterWordError("register words must be a list or tuple")
    if len(words) != kind.word_count:
        raise WordCountMismatchError(
            f"{kind.value} requires {kind.word_count} word(s); received {len(words)}"
        )
    validated = [_validate_word(word, index) for index, word in enumerate(words)]
    if kind.word_count == 2 and selected.word_order is WordOrder.LOW_WORD_FIRST:
        validated.reverse()
    restored = [_apply_byte_order(word, selected.byte_order) for word in validated]
    raw = restored[0] if kind.word_count == 1 else (restored[0] << 16) | restored[1]
    if kind.signed and raw >= 1 << (kind.bits - 1):
        return raw - (1 << kind.bits)
    return raw


def _validate_primitive(primitive: object) -> PrimitiveType:
    if not isinstance(primitive, PrimitiveType):
        raise UnsupportedPrimitiveTypeError("primitive must be a supported PrimitiveType")
    return primitive


def _validate_layout(kind: PrimitiveType, layout: CodecLayout | None) -> CodecLayout:
    if not isinstance(layout, CodecLayout):
        raise CodecConfigurationError("an explicit CodecLayout is required")
    if kind.word_count == 2 and layout.word_order is None:
        raise CodecConfigurationError("32-bit values require an explicit word order")
    if kind.word_count == 1 and layout.word_order is not None:
        raise CodecConfigurationError("16-bit values do not accept a word order")
    return layout


def _validate_word(word: object, index: int) -> int:
    if isinstance(word, bool) or not isinstance(word, int):
        raise RegisterWordError(f"register word {index} must be an integer, not bool")
    if not 0 <= word <= _WORD_MAX:
        raise RegisterWordError(f"register word {index} is outside [0, 65535]")
    return word


def _apply_byte_order(word: int, byte_order: ByteOrder) -> int:
    if byte_order is ByteOrder.BIG:
        return word
    return ((word & 0xFF) << 8) | (word >> 8)
