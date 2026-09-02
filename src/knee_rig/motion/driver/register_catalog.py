"""Conservative read-only catalog derived from supplied documentary evidence."""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from types import MappingProxyType
from typing import Final

from knee_rig.motion.driver.codec import PrimitiveType
from knee_rig.motion.driver.register_spec import (
    AccessClass,
    RegisterSpec,
    SafetyClass,
    VerificationStatus,
)


class UnknownRegisterError(LookupError):
    """A symbolic register is not in the reviewed catalog."""


_MANUAL = "A6-RS parameter-list manual; numeric address from historical project map"
_ADDRESS_CAUTION = (
    "Runtime zero/one-based convention and transport mapping require hardware verification."
)


def _spec(
    name: str,
    label: str,
    address: int,
    primitive: PrimitiveType,
    access: AccessClass,
    unit: str | None,
    scale: Fraction | None,
    safety: SafetyClass,
    *,
    machine_defining: bool = False,
    ordinary_operator_use: bool = False,
    engineering: bool = False,
    verification: VerificationStatus = VerificationStatus.HARDWARE_VERIFICATION_REQUIRED,
    caution: str = _ADDRESS_CAUTION,
) -> RegisterSpec:
    return RegisterSpec(
        name=name,
        manual_label=label,
        address=address,
        primitive=primitive,
        access=access,
        unit=unit,
        scale=scale,
        machine_defining=machine_defining,
        safety_class=safety,
        ordinary_operator_use=ordinary_operator_use,
        engineering_authorization_required=engineering,
        verification=verification,
        evidence_source=_MANUAL,
        caution=caution,
    )


_SPECS = (
    _spec(
        "POSITION_REFERENCE_SELECTION",
        "C03.00",
        0x0300,
        PrimitiveType.U16,
        AccessClass.READ_WRITE,
        None,
        None,
        SafetyClass.MACHINE_DEFINING,
        machine_defining=True,
        engineering=True,
    ),
    _spec(
        "GEAR_1_NUMERATOR",
        "C03.02",
        0x0302,
        PrimitiveType.U32,
        AccessClass.READ_WRITE,
        None,
        None,
        SafetyClass.MACHINE_DEFINING,
        machine_defining=True,
        engineering=True,
        caution=_ADDRESS_CAUTION + " 32-bit byte and word order are unverified.",
    ),
    _spec(
        "GEAR_1_DENOMINATOR",
        "C03.04",
        0x0304,
        PrimitiveType.U32,
        AccessClass.READ_WRITE,
        None,
        None,
        SafetyClass.MACHINE_DEFINING,
        machine_defining=True,
        engineering=True,
        caution=_ADDRESS_CAUTION + " 32-bit byte and word order are unverified.",
    ),
    _spec(
        "PLAN_MODE",
        "C11.00",
        0x1100,
        PrimitiveType.U16,
        AccessClass.READ_WRITE,
        None,
        None,
        SafetyClass.MOTION_CONFIGURATION,
        machine_defining=True,
        engineering=True,
    ),
    _spec(
        "GROUP_1_DISPLACEMENT",
        "C11.06",
        0x1106,
        PrimitiveType.I32,
        AccessClass.READ_WRITE,
        "application_unit",
        Fraction(1),
        SafetyClass.MOTION_CONFIGURATION,
        engineering=True,
        caution=_ADDRESS_CAUTION
        + " Application units are not joint degrees; 32-bit layout is unverified.",
    ),
    _spec(
        "SPEED_FEEDBACK",
        "U40.01",
        0x4001,
        PrimitiveType.I16,
        AccessClass.READ_ONLY,
        "rpm",
        Fraction(1),
        SafetyClass.TELEMETRY,
        ordinary_operator_use=True,
        verification=VerificationStatus.AMBIGUOUS,
        caution=_ADDRESS_CAUTION
        + " Manual table says I16 while nearby prose describes 32-bit; width remains ambiguous.",
    ),
    _spec(
        "TORQUE_FEEDBACK",
        "U40.03",
        0x4003,
        PrimitiveType.I16,
        AccessClass.READ_ONLY,
        "percent_rated_torque",
        Fraction(1, 10),
        SafetyClass.TELEMETRY,
        ordinary_operator_use=True,
    ),
    _spec(
        "BUS_VOLTAGE",
        "U40.06",
        0x4006,
        PrimitiveType.U16,
        AccessClass.READ_ONLY,
        "V",
        Fraction(1, 10),
        SafetyClass.TELEMETRY,
        ordinary_operator_use=True,
    ),
    _spec(
        "POSITION_DEVIATION",
        "U40.10",
        0x4010,
        PrimitiveType.I32,
        AccessClass.READ_ONLY,
        "encoder_pulse",
        Fraction(1),
        SafetyClass.TELEMETRY,
        ordinary_operator_use=True,
        caution=_ADDRESS_CAUTION + " 32-bit byte and word order are unverified.",
    ),
    _spec(
        "POSITION_FEEDBACK",
        "U40.16",
        0x4016,
        PrimitiveType.I32,
        AccessClass.READ_ONLY,
        "application_unit",
        Fraction(1),
        SafetyClass.TELEMETRY,
        ordinary_operator_use=True,
        caution=_ADDRESS_CAUTION
        + " Application units are not joint degrees; 32-bit layout is unverified.",
    ),
    _spec(
        "MOTOR_TEMPERATURE",
        "U40.31",
        0x4031,
        PrimitiveType.I16,
        AccessClass.READ_ONLY,
        "deg_C",
        Fraction(1, 10),
        SafetyClass.TELEMETRY,
        ordinary_operator_use=True,
    ),
    _spec(
        "ENCODER_TEMPERATURE",
        "U40.32",
        0x4032,
        PrimitiveType.I16,
        AccessClass.READ_ONLY,
        "deg_C",
        Fraction(1, 10),
        SafetyClass.TELEMETRY,
        ordinary_operator_use=True,
    ),
    _spec(
        "PLAN_OPERATION_GROUP",
        "U41.08",
        0x4108,
        PrimitiveType.U16,
        AccessClass.READ_ONLY,
        None,
        None,
        SafetyClass.STATUS,
        ordinary_operator_use=True,
    ),
    _spec(
        "SERVO_STATUS",
        "U41.0A",
        0x410A,
        PrimitiveType.U16,
        AccessClass.READ_ONLY,
        None,
        None,
        SafetyClass.STATUS,
        ordinary_operator_use=True,
    ),
)

REGISTER_CATALOG: Final[Mapping[str, RegisterSpec]] = MappingProxyType(
    {spec.name: spec for spec in _SPECS}
)


def get_register(name: str) -> RegisterSpec:
    try:
        return REGISTER_CATALOG[name]
    except KeyError as exc:
        raise UnknownRegisterError(f"unknown reviewed register: {name!r}") from exc


def list_registers() -> tuple[RegisterSpec, ...]:
    return _SPECS
