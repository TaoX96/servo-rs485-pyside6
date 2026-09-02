"""Synthetic offline records, never genuine device captures."""

from __future__ import annotations

import pytest

from knee_rig.motion.driver.fake_transport import (
    FakeReadOnlyTransport,
    FixtureFailure,
    ReadCall,
    RecordedWords,
)
from knee_rig.motion.driver.read_errors import (
    ChecksumError,
    ExtraResponseError,
    InvalidWordError,
    ProtocolExceptionError,
    ReadError,
    ShortResponseError,
    StaleResultError,
    TransportDisconnectedError,
    TransportTimeoutError,
    UnknownFixtureError,
)
from knee_rig.motion.driver.register_spec import RegisterArea
from knee_rig.motion.driver.transport import ReadOnlyRegisterTransport

AREA = RegisterArea.OFFLINE_FIXTURE
CALL = ReadCall(AREA, 0x410A, 1)


def test_known_fixture_exact_request_history_and_defensive_copy() -> None:
    fixtures = {CALL: RecordedWords((3,))}
    transport = FakeReadOnlyTransport(fixtures)
    fixtures.clear()
    assert transport.read_words(AREA, 0x410A, 1) == (3,)
    assert transport.history == (CALL,)
    with pytest.raises(UnknownFixtureError):
        transport.read_words(AREA, 0x410A, 2)
    assert len(transport.history) == 2


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (FixtureFailure.TIMEOUT, TransportTimeoutError),
        (FixtureFailure.DISCONNECTED, TransportDisconnectedError),
        (FixtureFailure.CHECKSUM, ChecksumError),
        (FixtureFailure.PROTOCOL, ProtocolExceptionError),
        (FixtureFailure.STALE, StaleResultError),
    ],
)
def test_injected_failure_does_not_retry(failure: FixtureFailure, error: type[ReadError]) -> None:
    transport = FakeReadOnlyTransport({CALL: RecordedWords(failure=failure)})
    with pytest.raises(error):
        transport.read_words(AREA, 0x410A, 1)
    assert transport.history == (CALL,)


@pytest.mark.parametrize(
    ("words", "error"),
    [
        ((), ShortResponseError),
        ((1, 2), ExtraResponseError),
        ((-1,), InvalidWordError),
        ((65536,), InvalidWordError),
        ((True,), InvalidWordError),
        ((1.0,), InvalidWordError),
        (("1",), InvalidWordError),
    ],
)
def test_malformed_record_is_not_padded_truncated_or_replaced(
    words: tuple[object, ...], error: type[ReadError]
) -> None:
    transport = FakeReadOnlyTransport({CALL: RecordedWords(words)})
    with pytest.raises(error):
        transport.read_words(AREA, 0x410A, 1)
    assert transport.history == (CALL,)


def test_unknown_fixture_history_is_bounded_and_read_only() -> None:
    transport = FakeReadOnlyTransport({})
    for _ in range(105):
        with pytest.raises(UnknownFixtureError):
            transport.read_words(AREA, 0x410A, 1)
    assert len(transport.history) == 100
    for interface in (ReadOnlyRegisterTransport, FakeReadOnlyTransport):
        assert not any(name.startswith("write") or name == "execute" for name in dir(interface))


def test_unresolved_area_and_invalid_requests_are_not_read() -> None:
    transport = FakeReadOnlyTransport({})
    with pytest.raises(ProtocolExceptionError):
        transport.read_words(RegisterArea.UNRESOLVED, 0x410A, 1)
    with pytest.raises(ProtocolExceptionError):
        transport.read_words(AREA, True, 1)
    with pytest.raises(ProtocolExceptionError):
        transport.read_words(AREA, 65535, 2)
    assert not transport.history
