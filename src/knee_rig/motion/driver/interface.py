"""Transport-free servo interface; no serial implementation exists through Milestone 3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from knee_rig.common.models import AlarmInfo, ServoStatus, TelemetrySnapshot


@dataclass(frozen=True, slots=True)
class OperationReceipt:
    accepted: bool
    completed: bool
    code: str | None = None
    message: str | None = None


class ServoInterface(Protocol):
    """Future real implementations belong exclusively to the Pi motion service."""

    def connect(self) -> OperationReceipt: ...

    def disconnect(self) -> OperationReceipt: ...

    def read_status(self) -> ServoStatus: ...

    def request_servo_enable(self) -> OperationReceipt: ...

    def request_servo_disable(self) -> OperationReceipt: ...

    def request_homing(self, *, timeout_ticks: int) -> OperationReceipt: ...

    def start_single_move(
        self,
        *,
        position_units: float,
        speed_units_per_tick: float,
    ) -> OperationReceipt: ...

    def start_cycle(
        self,
        *,
        positive_position_units: float,
        negative_position_units: float,
        speed_units_per_tick: float,
        cycle_count: int,
    ) -> OperationReceipt: ...

    def pause(self) -> OperationReceipt: ...

    def resume(self) -> OperationReceipt: ...

    def request_controlled_stop(self) -> OperationReceipt: ...

    def reset_fault(self) -> OperationReceipt: ...

    def read_telemetry(self) -> TelemetrySnapshot: ...

    def read_alarms(self) -> tuple[AlarmInfo, ...]: ...

    @property
    def completed_cycles(self) -> int: ...
