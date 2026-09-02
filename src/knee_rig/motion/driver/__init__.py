"""Reviewed transport-free driver contracts and register metadata."""

from knee_rig.motion.driver.codec import (
    ByteOrder,
    CodecConfigurationError,
    CodecLayout,
    PrimitiveType,
    RegisterCodecError,
    RegisterWordError,
    UnsupportedPrimitiveTypeError,
    ValueOutOfRangeError,
    WordCountMismatchError,
    WordOrder,
    decode_scalar,
    encode_scalar,
)
from knee_rig.motion.driver.interface import OperationReceipt, ServoInterface
from knee_rig.motion.driver.register_catalog import (
    REGISTER_CATALOG,
    UnknownRegisterError,
    get_register,
    list_registers,
)
from knee_rig.motion.driver.register_spec import (
    AccessClass,
    RegisterSpec,
    RegisterSpecValidationError,
    SafetyClass,
    VerificationStatus,
)

__all__ = [
    "REGISTER_CATALOG",
    "AccessClass",
    "ByteOrder",
    "CodecConfigurationError",
    "CodecLayout",
    "OperationReceipt",
    "PrimitiveType",
    "RegisterCodecError",
    "RegisterSpec",
    "RegisterSpecValidationError",
    "RegisterWordError",
    "SafetyClass",
    "ServoInterface",
    "UnknownRegisterError",
    "UnsupportedPrimitiveTypeError",
    "ValueOutOfRangeError",
    "VerificationStatus",
    "WordCountMismatchError",
    "WordOrder",
    "decode_scalar",
    "encode_scalar",
    "get_register",
    "list_registers",
]
