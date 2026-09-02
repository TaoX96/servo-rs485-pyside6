"""Windows simulation presentation; never owns or imports an RS485 transport."""

from knee_rig.gui.client import InProcessSimulationClient, MotionClient
from knee_rig.gui.main_window import MainWindow

__all__ = ["InProcessSimulationClient", "MainWindow", "MotionClient"]
