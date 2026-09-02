"""GUI-facing motion client contract with no transport or driver details."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from knee_rig.common.models import (
    AlarmInfo,
    AuthorizationDecision,
    CommandName,
    CommandPayload,
    CommandResult,
    StateSnapshot,
    TelemetrySnapshot,
)


@dataclass(frozen=True, slots=True)
class ClientActionResult:
    accepted: bool
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class LeaseSnapshot:
    active: bool
    lease_id: UUID | None = None
    expires_in_s: float | None = None


@dataclass(frozen=True, slots=True)
class ClientEvent:
    sequence: int
    category: str
    message: str


class SimulationFault(StrEnum):
    COMMUNICATION_LOSS = "communication_loss"
    DRIVE_FAULT = "drive_fault"
    HSW_NOT_FOUND = "hsw_not_found"
    HOMING_TIMEOUT = "homing_timeout"
    PL_ACTIVE = "pl_active"
    NL_ACTIVE = "nl_active"
    PL_AND_NL_ACTIVE = "pl_and_nl_active"
    CLEAR_LIMITS = "clear_limits"
    CONTROL_LEASE_EXPIRY = "control_lease_expiry"


class MotionClient(Protocol):
    """High-level interface shared by this adapter and a future network client."""

    def state(self) -> StateSnapshot: ...

    def telemetry(self) -> TelemetrySnapshot: ...

    def alarms(self) -> tuple[AlarmInfo, ...]: ...

    def completed_cycles(self) -> int: ...

    def lease(self) -> LeaseSnapshot: ...

    def events(self) -> tuple[ClientEvent, ...]: ...

    def connect(self) -> ClientActionResult: ...

    def disconnect(self) -> ClientActionResult: ...

    def acquire_lease(self) -> ClientActionResult: ...

    def renew_lease(self) -> ClientActionResult: ...

    def release_lease(self) -> ClientActionResult: ...

    def authorize(self, name: CommandName, payload: CommandPayload) -> AuthorizationDecision: ...

    def submit(
        self,
        name: CommandName,
        payload: CommandPayload,
        *,
        command_id: UUID | None = None,
    ) -> CommandResult: ...

    def advance(self, ticks: int = 1) -> None: ...

    def inject_fault(self, fault: SimulationFault) -> ClientActionResult: ...

    def shutdown(self) -> None: ...
