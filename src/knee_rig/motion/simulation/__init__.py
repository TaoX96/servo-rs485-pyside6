"""Deterministic, hardware-independent motion simulation."""

from knee_rig.motion.simulation.clock import ManualClock
from knee_rig.motion.simulation.fake_servo import FakeServo, HomingFailure

__all__ = ["FakeServo", "HomingFailure", "ManualClock"]
