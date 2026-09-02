"""Stable local/read-boundary failures; none imply a drive alarm."""


class ReadError(Exception):
    code = "READ_ERROR"


class ReadAuthorizationError(ReadError):
    code = "READ_NOT_AUTHORIZED"


class UnknownSymbolError(ReadError):
    code = "UNKNOWN_SYMBOL"


class UnresolvedAddressError(ReadError):
    code = "UNRESOLVED_ADDRESS"


class UnresolvedAreaError(ReadError):
    code = "UNRESOLVED_AREA"


class TransportError(ReadError):
    code = "TRANSPORT_ERROR"


class TransportDisconnectedError(TransportError):
    code = "TRANSPORT_DISCONNECTED"


class TransportTimeoutError(TransportError):
    code = "TRANSPORT_TIMEOUT"


class ChecksumError(TransportError):
    code = "CHECKSUM_FAILURE"


class ProtocolExceptionError(TransportError):
    code = "PROTOCOL_EXCEPTION"


class ShortResponseError(TransportError):
    code = "SHORT_RESPONSE"


class ExtraResponseError(TransportError):
    code = "EXTRA_RESPONSE"


class InvalidWordError(TransportError):
    code = "INVALID_WORD"


class UnknownFixtureError(TransportError):
    code = "UNKNOWN_FIXTURE"


class StaleResultError(TransportError):
    code = "STALE_RESULT"


class DecodeFailureError(ReadError):
    code = "DECODE_FAILURE"


class UnverifiedLayoutError(ReadError):
    code = "UNVERIFIED_LAYOUT"


class AmbiguousRegisterError(ReadError):
    code = "AMBIGUOUS_REGISTER"


class SnapshotIncompleteError(ReadError):
    code = "SNAPSHOT_INCOMPLETE"
