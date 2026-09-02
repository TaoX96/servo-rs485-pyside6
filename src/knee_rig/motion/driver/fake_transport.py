"""In-memory synthetic words and deterministic injected failures; no device I/O."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from knee_rig.motion.driver.read_errors import (
    ChecksumError,
    ProtocolExceptionError,
    StaleResultError,
    TransportDisconnectedError,
    TransportTimeoutError,
    UnknownFixtureError,
)
from knee_rig.motion.driver.register_spec import RegisterArea
from knee_rig.motion.driver.transport import ReadSource, validate_response


@dataclass(frozen=True, slots=True)
class ReadCall:
    area: RegisterArea
    address: int
    count: int


class FixtureFailure(StrEnum):
    TIMEOUT = "timeout"
    DISCONNECTED = "disconnected"
    CHECKSUM = "checksum"
    PROTOCOL = "protocol"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class RecordedWords:
    """Synthetic record, not a genuine A6-RS capture; invalid words test failures."""

    words: tuple[object, ...] = ()
    failure: FixtureFailure | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.words, tuple):
            raise TypeError("fixture words must be an immutable tuple")
        if self.failure is not None and not isinstance(self.failure, FixtureFailure):
            raise TypeError("failure must be a FixtureFailure")


class FakeReadOnlyTransport:
    def __init__(self, fixtures: Mapping[ReadCall, RecordedWords]) -> None:
        self._fixtures = MappingProxyType(dict(fixtures))
        self._history: deque[ReadCall] = deque(maxlen=100)

    @property
    def source(self) -> ReadSource:
        return ReadSource.SYNTHETIC_FIXTURE

    @property
    def history(self) -> tuple[ReadCall, ...]:
        return tuple(self._history)

    def read_words(self, area: RegisterArea, address: int, count: int) -> tuple[int, ...]:
        if area is not RegisterArea.OFFLINE_FIXTURE:
            raise ProtocolExceptionError("fake reads require the offline fixture area")
        if type(address) is not int or not 0 <= address <= 65535:
            raise ProtocolExceptionError("invalid fixture address")
        if type(count) is not int or not 1 <= count <= 2 or address + count > 65536:
            raise ProtocolExceptionError("invalid fixture word count or span")
        call = ReadCall(area, address, count)
        self._history.append(call)
        record = self._fixtures.get(call)
        if record is None:
            raise UnknownFixtureError("no synthetic fixture for the exact read request")
        failures = {
            FixtureFailure.TIMEOUT: TransportTimeoutError,
            FixtureFailure.DISCONNECTED: TransportDisconnectedError,
            FixtureFailure.CHECKSUM: ChecksumError,
            FixtureFailure.PROTOCOL: ProtocolExceptionError,
            FixtureFailure.STALE: StaleResultError,
        }
        if record.failure is not None:
            raise failures[record.failure]("deterministic synthetic transport failure")
        return validate_response(record.words, count)
