"""Minimum read-only boundary; no physical adapter exists."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from knee_rig.motion.driver.read_errors import (
    ExtraResponseError,
    InvalidWordError,
    ProtocolExceptionError,
    ShortResponseError,
)
from knee_rig.motion.driver.register_spec import RegisterArea


class ReadSource(StrEnum):
    SYNTHETIC_FIXTURE = "synthetic-offline-fixture"


class ReadOnlyRegisterTransport(Protocol):
    @property
    def source(self) -> ReadSource: ...

    def read_words(self, area: RegisterArea, address: int, count: int) -> tuple[int, ...]:
        """Return exactly count immutable words or raise a typed boundary error."""
        ...


def validate_response(words: object, count: int) -> tuple[int, ...]:
    """Validate even responses from a nonconforming injected implementation."""
    if not isinstance(words, tuple):
        raise ProtocolExceptionError("response must be an immutable tuple")
    if len(words) < count:
        raise ShortResponseError("response contains fewer words than requested")
    if len(words) > count:
        raise ExtraResponseError("response contains more words than requested")
    for word in words:
        if isinstance(word, bool) or not isinstance(word, int) or not 0 <= word <= 65535:
            raise InvalidWordError("response contains an invalid 16-bit word")
    return words
