"""Hardware-independent driver contract owned only by the future Pi motion service."""

from knee_rig.motion.driver.interface import OperationReceipt, ServoInterface

__all__ = ["OperationReceipt", "ServoInterface"]

