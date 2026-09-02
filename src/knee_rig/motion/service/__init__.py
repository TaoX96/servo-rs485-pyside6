"""In-process simulation coordinator; no HTTP or background service exists."""

from knee_rig.motion.service.core import MotionCoordinator

__all__ = ["MotionCoordinator"]
