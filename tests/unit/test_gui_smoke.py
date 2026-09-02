"""Offscreen PySide6 smoke tests for safe simulation GUI behavior."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton
from pytestqt.qtbot import QtBot

from knee_rig.common.models import (
    CommandName,
    CommandStatus,
    HomingState,
    MotionState,
    ServoState,
    SingleMovePayload,
)
from knee_rig.gui.client import InProcessSimulationClient
from knee_rig.gui.main_window import MainWindow


def _window(qtbot: QtBot) -> tuple[MainWindow, InProcessSimulationClient]:
    client = InProcessSimulationClient()
    window = MainWindow(client)
    qtbot.addWidget(window)
    window.show()
    return window, client


def test_window_creation_safe_state_and_core_controls(qtbot: QtBot) -> None:
    window, client = _window(qtbot)

    assert window.findChild(QLabel, "simulationIndicator").text().startswith("SIMULATION")
    assert client.state().servo is ServoState.SERVO_DISABLED
    assert client.state().homing is HomingState.UNHOMED
    assert client.state().motion is MotionState.IDLE
    assert not any(event.category == "command" for event in client.events())
    assert window.findChild(QPushButton, "command_controlled_stop").text() == "Controlled Stop"
    required_controls = {
        "connectButton",
        "disconnectButton",
        "acquireLeaseButton",
        "renewLeaseButton",
        "releaseLeaseButton",
        "command_enable_servo",
        "command_disable_servo",
        "command_home",
        "command_start_single_move",
        "command_start_cycle",
        "command_pause",
        "command_resume",
        "command_controlled_stop",
        "command_reset_fault",
        "inject_communication_loss",
        "inject_drive_fault",
        "inject_hsw_not_found",
        "inject_homing_timeout",
        "inject_pl_active",
        "inject_nl_active",
        "inject_pl_and_nl_active",
        "inject_control_lease_expiry",
    }
    assert required_controls <= {button.objectName() for button in window.findChildren(QPushButton)}
    button_texts = [button.text() for button in window.findChildren(QPushButton)]
    assert "Emergency Stop" not in button_texts
    assert "E-Stop" not in button_texts


def test_rejected_then_authorized_command_flow_and_validation(qtbot: QtBot) -> None:
    window, client = _window(qtbot)
    enable = window.findChild(QPushButton, "command_enable_servo")
    assert not enable.isEnabled()

    window.findChild(QPushButton, "connectButton").click()
    window.findChild(QPushButton, "acquireLeaseButton").click()
    assert enable.isEnabled()
    enable.click()
    assert client.state().servo is ServoState.SERVO_ENABLED

    window.findChild(QPushButton, "command_home").click()
    client.advance(3)
    window.refresh_view()
    assert client.state().homing is HomingState.HOMED

    move = window.findChild(QPushButton, "command_start_single_move")
    assert move.isEnabled()
    window.target_input.setText("not-a-number")
    move.click()
    assert "must be a number" in window.validation_label.text()
    assert client.state().motion is MotionState.IDLE

    window.target_input.setText("101")
    move.click()
    assert "between -100 and 100" in window.validation_label.text()
    assert client.state().motion is MotionState.IDLE

    window.target_input.setText("4")
    move.click()
    assert client.state().motion is MotionState.STARTING
    assert "acceptance is not operation completion" in window.statusBar().currentMessage()


def test_close_during_motion_stops_timer_and_requires_recovery(qtbot: QtBot) -> None:
    window, client = _window(qtbot)
    window.findChild(QPushButton, "connectButton").click()
    window.findChild(QPushButton, "acquireLeaseButton").click()
    window.findChild(QPushButton, "command_enable_servo").click()
    window.findChild(QPushButton, "command_home").click()
    client.advance(3)
    window.refresh_view()
    window.findChild(QPushButton, "command_start_single_move").click()
    client.advance(1)
    assert window.isVisible()
    assert client.state().motion is MotionState.MOVING
    active_command_id = client.state().active_command_id
    assert active_command_id is not None

    window.close()

    assert not window.isVisible()
    assert not window.simulation_timer_active
    assert client.state().motion is MotionState.IDLE
    assert client.state().servo is ServoState.SERVO_ENABLED
    assert client.state().homing is not HomingState.HOMING
    assert client.state().active_command_id is None
    assert client.state().recovery_required
    assert client.state().active_fault_code == "CONTROL_LEASE_EXPIRED"
    replay = client.submit(
        CommandName.START_SINGLE_MOVE,
        SingleMovePayload(position_units=10.0, speed_units_per_tick=1.0),
        command_id=active_command_id,
    )
    assert replay.status is CommandStatus.CANCELLED
    assert any(
        event.category == "shutdown" and "controlled stop requested" in event.message
        for event in client.events()
    )
