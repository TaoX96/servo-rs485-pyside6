"""Synchronous symbolic offline reads, without polling, caching or motion coupling."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from knee_rig.motion.driver.codec import CodecLayout, RegisterCodecError, decode_scalar
from knee_rig.motion.driver.read_errors import (
    DecodeFailureError,
    ReadAuthorizationError,
    ReadError,
    UnknownSymbolError,
    UnresolvedAddressError,
    UnresolvedAreaError,
    UnverifiedLayoutError,
)
from knee_rig.motion.driver.read_models import (
    DecodedReadResult,
    LayoutVerification,
    RawReadResult,
    ReadClock,
    ReadFailure,
    ReadValidity,
    SnapshotField,
    StatusSnapshot,
)
from knee_rig.motion.driver.register_catalog import UnknownRegisterError, get_register
from knee_rig.motion.driver.register_spec import AccessClass, RegisterArea, VerificationStatus
from knee_rig.motion.driver.transport import (
    ReadOnlyRegisterTransport,
    ReadSource,
    validate_response,
)

OPERATIONAL_READS: Final = frozenset(
    {
        "SERVO_STATUS",
        "POSITION_FEEDBACK",
        "SPEED_FEEDBACK",
        "TORQUE_FEEDBACK",
        "BUS_VOLTAGE",
        "POSITION_DEVIATION",
        "MOTOR_TEMPERATURE",
        "ENCODER_TEMPERATURE",
        "PLAN_OPERATION_GROUP",
    }
)
ENGINEERING_READS: Final = frozenset(
    {
        "POSITION_REFERENCE_SELECTION",
        "GEAR_1_NUMERATOR",
        "GEAR_1_DENOMINATOR",
        "PLAN_MODE",
    }
)
DEFAULT_SNAPSHOT: Final = tuple(sorted(OPERATIONAL_READS))


@dataclass(frozen=True, slots=True)
class OfflineFixtureInterpretation:
    """Explicit fixture-only area override and per-symbol layouts; no hardware trust."""

    layouts: Mapping[str, CodecLayout]

    def __post_init__(self) -> None:
        for symbol, layout in self.layouts.items():
            if symbol not in OPERATIONAL_READS | ENGINEERING_READS:
                raise ReadAuthorizationError("fixture layout symbol is not allowlisted")
            if not isinstance(layout, CodecLayout):
                raise DecodeFailureError("fixture layout must be a CodecLayout")
        object.__setattr__(self, "layouts", MappingProxyType(dict(self.layouts)))


class ReadOnlyServoReader:
    def __init__(
        self,
        transport: ReadOnlyRegisterTransport,
        clock: ReadClock,
        *,
        fixture_interpretation: OfflineFixtureInterpretation | None = None,
        engineering_read_permission: bool = False,
    ) -> None:
        if type(engineering_read_permission) is not bool:
            raise ReadAuthorizationError("engineering permission must be an explicit bool")
        self._transport = transport
        self._clock = clock
        self._fixture_interpretation = fixture_interpretation
        self._engineering = engineering_read_permission
        self._sequence = 0
        self._snapshot_sequence = 0

    def read(self, symbol: str) -> DecodedReadResult:
        if not isinstance(symbol, str) or len(symbol) > 80:
            raise UnknownSymbolError("a bounded symbolic register name is required")
        try:
            spec = get_register(symbol)
        except UnknownRegisterError as exc:
            raise UnknownSymbolError("unknown symbolic register") from exc
        if symbol in ENGINEERING_READS:
            if not self._engineering:
                raise ReadAuthorizationError("engineering inspection is disabled")
        elif (
            symbol not in OPERATIONAL_READS
            or spec.access is not AccessClass.READ_ONLY
            or spec.machine_defining
            or not spec.ordinary_operator_use
        ):
            raise ReadAuthorizationError("register is not operationally allowlisted")
        if spec.address is None:
            raise UnresolvedAddressError("register runtime address is unresolved")
        interpretation = self._fixture_interpretation
        if interpretation is None:
            raise UnresolvedAreaError("register area/function code requires an offline override")
        if self._transport.source is not ReadSource.SYNTHETIC_FIXTURE:
            raise ReadAuthorizationError("fixture interpretation requires a synthetic source")
        layout = interpretation.layouts.get(symbol)
        ambiguous = spec.verification is VerificationStatus.AMBIGUOUS
        if (
            not ambiguous
            and spec.primitive.word_count == 2
            and (layout is None or layout.word_order is None)
        ):
            raise UnverifiedLayoutError(
                "32-bit hardware layout is unverified; fixture layout required"
            )
        self._sequence += 1
        words = validate_response(
            self._transport.read_words(
                RegisterArea.OFFLINE_FIXTURE, spec.address, spec.primitive.word_count
            ),
            spec.primitive.word_count,
        )
        raw = RawReadResult(
            symbol=symbol,
            manual_label=spec.manual_label,
            address=spec.address,
            area=RegisterArea.OFFLINE_FIXTURE,
            catalog_area=spec.area,
            requested_count=spec.primitive.word_count,
            words=words,
            sequence=self._sequence,
            acquired_at=self._clock.wall_time,
            monotonic_s=self._clock.monotonic_s,
            source=self._transport.source,
            validity=ReadValidity.FIXTURE_VALID,
            documentary_verification=spec.verification,
            layout_verification=LayoutVerification.HARDWARE_UNVERIFIED,
        )
        scalar: int | None = None
        if not ambiguous:
            try:
                scalar = decode_scalar(words, spec.primitive, layout)
            except RegisterCodecError as exc:
                raise DecodeFailureError(f"local codec failure: {type(exc).__name__}") from exc
        return DecodedReadResult(
            raw=raw,
            primitive=spec.primitive,
            scalar=scalar,
            unit=spec.unit,
            scale=spec.scale,
            validity=ReadValidity.AMBIGUOUS if ambiguous else ReadValidity.FIXTURE_VALID,
            ambiguity=(spec.caution[:256],) if ambiguous else (),
            layout=None if ambiguous else layout,
            layout_verification=LayoutVerification.HARDWARE_UNVERIFIED,
            evidence_source=spec.evidence_source,
            documentary_verification=spec.verification,
        )

    def snapshot(self, symbols: tuple[str, ...] = DEFAULT_SNAPSHOT) -> StatusSnapshot:
        if not isinstance(symbols, tuple) or not 1 <= len(symbols) <= len(OPERATIONAL_READS):
            raise ReadAuthorizationError("snapshot requires a bounded tuple of operational symbols")
        if any(
            not isinstance(symbol, str) or symbol not in OPERATIONAL_READS for symbol in symbols
        ):
            raise ReadAuthorizationError("snapshots are operational only")
        if len(set(symbols)) != len(symbols):
            raise ReadAuthorizationError("snapshot symbols must be unique")
        fields = []
        for symbol in symbols:
            try:
                result = self.read(symbol)
                fields.append(SnapshotField(symbol, result, None))
            except ReadError as exc:
                # Do not publish arbitrary lower-layer exception messages or payloads.
                fields.append(
                    SnapshotField(symbol, None, ReadFailure(exc.code, "offline field read failed"))
                )
        self._snapshot_sequence += 1
        degraded = any(
            field.failure is not None
            or (
                field.result is not None and field.result.validity is not ReadValidity.FIXTURE_VALID
            )
            for field in fields
        )
        return StatusSnapshot(
            sequence=self._snapshot_sequence,
            acquired_at=self._clock.wall_time,
            monotonic_s=self._clock.monotonic_s,
            source=ReadSource.SYNTHETIC_FIXTURE,
            validity=ReadValidity.DEGRADED if degraded else ReadValidity.FIXTURE_VALID,
            fields=tuple(fields),
        )
