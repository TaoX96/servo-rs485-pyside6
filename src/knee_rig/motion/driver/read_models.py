"""Immutable offline read observations, with trust separate from codec success."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from fractions import Fraction
from typing import Protocol

from knee_rig.motion.driver.codec import CodecLayout, PrimitiveType
from knee_rig.motion.driver.register_spec import RegisterArea, VerificationStatus
from knee_rig.motion.driver.transport import ReadSource


class ReadClock(Protocol):
    @property
    def wall_time(self) -> datetime: ...

    @property
    def monotonic_s(self) -> float: ...


class ReadValidity(StrEnum):
    FIXTURE_VALID = "fixture_valid_not_hardware_verified"
    AMBIGUOUS = "ambiguous"
    DEGRADED = "degraded"


class LayoutVerification(StrEnum):
    HARDWARE_UNVERIFIED = "hardware_unverified"


@dataclass(frozen=True, slots=True)
class RawReadResult:
    symbol: str
    manual_label: str
    address: int
    area: RegisterArea
    catalog_area: RegisterArea
    requested_count: int
    words: tuple[int, ...]
    sequence: int
    acquired_at: datetime
    monotonic_s: float
    source: ReadSource
    validity: ReadValidity
    documentary_verification: VerificationStatus
    layout_verification: LayoutVerification
    fresh_at_acquisition: bool = True
    diagnostics: tuple[str, ...] = ("synthetic fixture interpretation only",)


@dataclass(frozen=True, slots=True)
class DecodedReadResult:
    raw: RawReadResult
    primitive: PrimitiveType
    scalar: int | None
    unit: str | None
    scale: Fraction | None
    validity: ReadValidity
    ambiguity: tuple[str, ...]
    layout: CodecLayout | None
    layout_verification: LayoutVerification
    evidence_source: str
    documentary_verification: VerificationStatus
    # No physical scaling layer or mechanical conversion is implemented.


@dataclass(frozen=True, slots=True)
class ReadFailure:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class SnapshotField:
    symbol: str
    result: DecodedReadResult | None
    failure: ReadFailure | None


@dataclass(frozen=True, slots=True)
class StatusSnapshot:
    sequence: int
    acquired_at: datetime
    monotonic_s: float
    source: ReadSource
    validity: ReadValidity
    fields: tuple[SnapshotField, ...]
