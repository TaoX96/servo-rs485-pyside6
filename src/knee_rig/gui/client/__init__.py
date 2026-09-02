"""High-level GUI client boundary."""

from knee_rig.gui.client.in_process import InProcessSimulationClient, simulation_gui_config
from knee_rig.gui.client.interface import (
    ClientActionResult,
    ClientEvent,
    LeaseSnapshot,
    MotionClient,
    SimulationFault,
)

__all__ = [
    "ClientActionResult",
    "ClientEvent",
    "InProcessSimulationClient",
    "LeaseSnapshot",
    "MotionClient",
    "SimulationFault",
    "simulation_gui_config",
]
