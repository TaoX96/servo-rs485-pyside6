"""The catalog is read-only documentary metadata, never a hardware access API."""

from __future__ import annotations

from fractions import Fraction
from typing import cast

import pytest

from knee_rig.motion import driver
from knee_rig.motion.driver import (
    REGISTER_CATALOG,
    AccessClass,
    PrimitiveType,
    SafetyClass,
    UnknownRegisterError,
    VerificationStatus,
    get_register,
    list_registers,
)


def test_catalog_lookup_and_unknown_register_error() -> None:
    assert get_register("SERVO_STATUS").manual_label == "U41.0A"
    with pytest.raises(UnknownRegisterError):
        get_register("ARBITRARY_REGISTER")


def test_catalog_and_specs_are_immutable() -> None:
    with pytest.raises(TypeError):
        mutable_view = cast(dict[str, object], REGISTER_CATALOG)
        mutable_view["NEW"] = get_register("SERVO_STATUS")
    assert tuple(REGISTER_CATALOG.values()) == list_registers()


def test_verification_and_engineering_classification_are_preserved() -> None:
    for spec in list_registers():
        assert spec.verification in {
            VerificationStatus.MANUAL_CONFIRMED,
            VerificationStatus.AMBIGUOUS,
            VerificationStatus.HARDWARE_VERIFICATION_REQUIRED,
        }
    gear = get_register("GEAR_1_NUMERATOR")
    assert gear.machine_defining
    assert gear.engineering_authorization_required
    assert not gear.ordinary_operator_use
    assert gear.safety_class is SafetyClass.MACHINE_DEFINING


def test_exact_scales_and_application_units_are_not_joint_degrees() -> None:
    assert get_register("MOTOR_TEMPERATURE").scale == Fraction(1, 10)
    assert get_register("BUS_VOLTAGE").scale == Fraction(1, 10)
    position = get_register("POSITION_FEEDBACK")
    assert position.unit == "application_unit"
    assert "degree" not in position.unit


def test_addresses_are_preserved_without_automatic_adjustment() -> None:
    assert get_register("SERVO_STATUS").address == 0x410A
    assert get_register("GROUP_1_DISPLACEMENT").address == 0x1106
    assert all("no offset applied" in spec.address_notation for spec in list_registers())


def test_width_ambiguity_and_unverified_layout_remain_explicit() -> None:
    speed = get_register("SPEED_FEEDBACK")
    assert speed.primitive is PrimitiveType.I16
    assert speed.verification is VerificationStatus.AMBIGUOUS
    assert "width remains ambiguous" in speed.caution
    assert "layout is unverified" in get_register("POSITION_FEEDBACK").caution


def test_public_driver_api_has_no_arbitrary_hardware_access() -> None:
    prohibited = {"read_register", "write_register", "connect_serial", "modbus_client"}
    assert prohibited.isdisjoint(dir(driver))
    assert get_register("TORQUE_FEEDBACK").access is AccessClass.READ_ONLY
