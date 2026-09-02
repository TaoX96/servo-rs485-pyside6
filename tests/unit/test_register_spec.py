"""Register metadata is immutable, derived, exact, and fail-closed."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from fractions import Fraction
from typing import Any

import pytest

from knee_rig.motion.driver import (
    AccessClass,
    PrimitiveType,
    RegisterSpec,
    RegisterSpecValidationError,
    SafetyClass,
    VerificationStatus,
)


def _spec(**changes: object) -> RegisterSpec:
    values: dict[str, Any] = {
        "name": "TEST",
        "manual_label": "U00.00",
        "address": 0,
        "primitive": PrimitiveType.I32,
        "access": AccessClass.READ_ONLY,
        "unit": "application_unit",
        "scale": Fraction(1),
        "machine_defining": False,
        "safety_class": SafetyClass.TELEMETRY,
        "ordinary_operator_use": True,
        "engineering_authorization_required": False,
        "verification": VerificationStatus.MANUAL_CONFIRMED,
        "evidence_source": "supplied manual",
        "caution": "Documentary confirmation is not physical-drive verification.",
    }
    values.update(changes)
    return RegisterSpec(**values)


def test_word_count_and_signedness_are_derived_and_spec_is_immutable() -> None:
    spec = _spec()
    assert spec.word_count == 2
    assert spec.signed
    with pytest.raises(FrozenInstanceError):
        spec.address = 1


def test_contradictory_word_count_and_signedness_are_rejected() -> None:
    with pytest.raises(RegisterSpecValidationError):
        _spec(word_count=1)
    with pytest.raises(RegisterSpecValidationError):
        _spec(signed=False)


@pytest.mark.parametrize("address", (-1, 65536, True))
def test_invalid_addresses_are_rejected(address: object) -> None:
    with pytest.raises(RegisterSpecValidationError):
        _spec(address=address)


def test_physical_unit_requires_exact_scale() -> None:
    with pytest.raises(RegisterSpecValidationError):
        _spec(scale=None)
    with pytest.raises(RegisterSpecValidationError):
        _spec(scale=0.1)


def test_machine_defining_register_cannot_be_operator_accessible() -> None:
    with pytest.raises(RegisterSpecValidationError):
        _spec(machine_defining=True, ordinary_operator_use=True)


def test_read_only_register_cannot_require_write_authorization() -> None:
    with pytest.raises(RegisterSpecValidationError):
        _spec(engineering_authorization_required=True)
