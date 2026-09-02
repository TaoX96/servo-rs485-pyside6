"""A deterministic clock advanced explicitly by tests or the simulation host."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(slots=True)
class ManualClock:
    monotonic_s: float = 0.0
    wall_time: datetime = datetime(2026, 1, 1, tzinfo=UTC)

    def advance(self, seconds: float = 1.0) -> None:
        if seconds <= 0:
            raise ValueError("seconds must be greater than zero")
        self.monotonic_s += seconds
        self.wall_time += timedelta(seconds=seconds)
