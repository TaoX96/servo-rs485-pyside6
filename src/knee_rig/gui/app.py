"""Launch the simulation-only PySide6 application."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from knee_rig.gui.client import InProcessSimulationClient
from knee_rig.gui.main_window import MainWindow


def create_window() -> MainWindow:
    """Create a safely initialized simulation window without issuing commands."""
    return MainWindow(InProcessSimulationClient())


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    window = create_window()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
