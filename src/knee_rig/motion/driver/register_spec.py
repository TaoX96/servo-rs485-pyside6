"""Immutable documentary metadata for registers; never an access authorization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from knee_rig.motion.driver.codec import PrimitiveType


class RegisterSpecValidationError(ValueError):
    """Register metadata is contradictory or unsafe."""


class AccessClass(StrEnum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    WRITE_OR_TRIGGER = "write_or_trigger"
    UNKNOWN = "unknown"


class SafetyClass(StrEnum):
    STATUS = "status"
    TELEMETRY = "telemetry"
    MOTION_CONFIGURATION = "motion_configuration"
    MACHINE_DEFINING = "machine_defining"
    SAFETY_RELEVANT_CONFIGURATION = "safety_relevant_configuration"


class VerificationStatus(StrEnum):
    MANUAL_CONFIRMED = "manual_confirmed"
    LEGACY_CODE_ONLY = "legacy_code_only"
    MANUAL_AND_LEGACY_AGREE = "manual_and_legacy_agree"
    AMBIGUOUS = "ambiguous"
    HARDWARE_VERIFICATION_REQUIRED = "hardware_verification_required"


class RegisterArea(StrEnum):
    """No real register-area or function-code mapping has been established."""

    UNRESOLVED = "unresolved"
    OFFLINE_FIXTURE = "offline_fixture"


@dataclass(frozen=True, slots=True)
class RegisterSpec:
    name: str
    manual_label: str
    address: int | None
    primitive: PrimitiveType
    access: AccessClass
    unit: str | None
    scale: Fraction | None
    machine_defining: bool
    safety_class: SafetyClass
    ordinary_operator_use: bool
    engineering_authorization_required: bool
    verification: VerificationStatus
    evidence_source: str
    caution: str
    address_notation: str = "historical zero-based runtime address; no offset applied"
    word_count: int | None = None
    signed: bool | None = None
    area: RegisterArea = RegisterArea.UNRESOLVED

    def __post_init__(self) -> None:
        if not self.name or not self.manual_label or not self.evidence_source:
            raise RegisterSpecValidationError("name, manual label, and evidence are required")
        if not isinstance(self.area, RegisterArea):
            raise RegisterSpecValidationError("area must be an explicit RegisterArea")
        if self.address is not None and (
            isinstance(self.address, bool)
            or not isinstance(self.address, int)
            or not 0 <= self.address <= 0xFFFF
        ):
            raise RegisterSpecValidationError("address must be None or an integer in [0, 65535]")
        if not isinstance(self.primitive, PrimitiveType):
            raise RegisterSpecValidationError("primitive must be a PrimitiveType")
        if self.word_count is not None and self.word_count != self.primitive.word_count:
            raise RegisterSpecValidationError("word count contradicts the primitive type")
        if self.signed is not None and self.signed is not self.primitive.signed:
            raise RegisterSpecValidationError("signedness contradicts the primitive type")
        object.__setattr__(self, "word_count", self.primitive.word_count)
        object.__setattr__(self, "signed", self.primitive.signed)
        if not isinstance(self.access, AccessClass):
            raise RegisterSpecValidationError("access must be an AccessClass")
        if self.unit is not None and self.scale is None:
            raise RegisterSpecValidationError("a documented unit requires an exact scale")
        if self.scale is not None and (not isinstance(self.scale, Fraction) or self.scale <= 0):
            raise RegisterSpecValidationError("scale must be a positive Fraction or None")
        if self.machine_defining and self.ordinary_operator_use:
            raise RegisterSpecValidationError(
                "machine-defining registers cannot be ordinary-operator accessible"
            )
        if self.access is AccessClass.READ_ONLY and self.engineering_authorization_required:
            raise RegisterSpecValidationError(
                "read-only metadata cannot require write authorization"
            )
        if not isinstance(self.verification, VerificationStatus):
            raise RegisterSpecValidationError("verification must preserve documentary status")
