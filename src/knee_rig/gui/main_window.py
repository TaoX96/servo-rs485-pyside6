"""Minimal operator-facing Qt window for in-process simulation only."""

from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from knee_rig.common.models import (
    CommandName,
    CommandPayload,
    ControlledStopPayload,
    CyclePayload,
    DisableServoPayload,
    EnableServoPayload,
    HomePayload,
    PausePayload,
    ResetFaultPayload,
    ResumePayload,
    SingleMovePayload,
)
from knee_rig.gui.client import ClientActionResult, MotionClient, SimulationFault
from knee_rig.gui.presenter import MainView, present


class InputValidationError(ValueError):
    """A bounded operator input could not be represented safely."""


class MainWindow(QMainWindow):
    """Present simulation state and submit only typed high-level commands."""

    def __init__(self, client: MotionClient) -> None:
        super().__init__()
        self._client = client
        self._last_event_sequence = 0
        self.setWindowTitle("Knee Rig — In-Process Simulation")
        self.setMinimumSize(880, 720)
        self._state_labels: dict[str, QLabel] = {}
        self._telemetry_labels: dict[str, QLabel] = {}
        self._action_buttons: dict[str, QPushButton] = {}
        self._command_buttons: dict[CommandName, QPushButton] = {}
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()
        self.refresh_view()

    def _build_ui(self) -> None:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.addWidget(self._build_banner())
        middle = QHBoxLayout()
        middle.addWidget(self._build_telemetry(), 1)
        middle.addWidget(self._build_parameters(), 1)
        layout.addLayout(middle)
        layout.addWidget(self._build_commands())
        layout.addWidget(self._build_simulation_panel())
        layout.addWidget(self._build_events(), 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        self.setCentralWidget(scroll)

    def _build_banner(self) -> QGroupBox:
        box = QGroupBox("Connection and safety")
        layout = QGridLayout(box)
        simulation = QLabel("SIMULATION — NO REAL HARDWARE CONTROL")
        simulation.setObjectName("simulationIndicator")
        simulation.setStyleSheet("font-size: 18px; font-weight: bold; color: #7a3e00;")
        layout.addWidget(simulation, 0, 0, 1, 4)
        safety = QLabel(
            "Controlled Stop is ordinary simulation software control. It is not an emergency stop "
            "and cannot replace an independent hardware emergency-stop circuit."
        )
        safety.setWordWrap(True)
        safety.setStyleSheet("font-weight: bold;")
        layout.addWidget(safety, 1, 0, 1, 4)
        fields = (
            ("service", "Service"),
            ("connection", "Simulated connection"),
            ("servo", "Servo"),
            ("homing", "Homing"),
            ("homing_reference", "Selected homing reference"),
            ("homing_phase", "Simulated homing phase"),
            ("motion", "Motion"),
            ("lease", "Control lease"),
            ("motion_permitted", "Motion commands permitted"),
            ("fault", "Fault"),
        )
        for index, (key, title) in enumerate(fields):
            label = QLabel("Unavailable")
            label.setObjectName(f"state_{key}")
            self._state_labels[key] = label
            row = 2 + index // 2
            column = (index % 2) * 2
            layout.addWidget(QLabel(f"{title}:"), row, column)
            layout.addWidget(label, row, column + 1)
        return box

    def _build_telemetry(self) -> QGroupBox:
        box = QGroupBox("Telemetry")
        form = QFormLayout(box)
        fields = (
            ("position", "Position"),
            ("velocity", "Velocity"),
            ("torque", "Torque"),
            ("timestamp", "Timestamp"),
            ("sequence", "Sequence"),
            ("freshness", "Validity / freshness"),
            ("pl", "PL"),
            ("nl", "NL"),
            ("hsw", "HSW (deferred / unused)"),
            ("cycle_progress", "Finite-cycle progress"),
        )
        for key, title in fields:
            label = QLabel("Unavailable")
            label.setObjectName(f"telemetry_{key}")
            label.setTextInteractionFlags(label.textInteractionFlags())
            self._telemetry_labels[key] = label
            form.addRow(f"{title}:", label)
        return box

    def _build_parameters(self) -> QGroupBox:
        box = QGroupBox("Simulation parameters")
        form = QFormLayout(box)
        self.target_input = self._input("10", "targetInput")
        self.positive_input = self._input("10", "positiveInput")
        self.negative_input = self._input("-10", "negativeInput")
        self.speed_input = self._input("1", "speedInput")
        self.cycle_count_input = self._input("2", "cycleCountInput")
        self.homing_timeout_input = self._input("20", "homingTimeoutInput")
        form.addRow("Move target (application units):", self.target_input)
        form.addRow("Cycle positive target (application units):", self.positive_input)
        form.addRow("Cycle negative target (application units):", self.negative_input)
        form.addRow("Speed (application units/tick):", self.speed_input)
        form.addRow("Finite cycle count (1–10):", self.cycle_count_input)
        form.addRow("Homing timeout (ticks):", self.homing_timeout_input)
        note = QLabel(
            "Angle input is unavailable because calibration is unverified. Acceleration and "
            "deceleration are not represented by the Milestone 1 simulation command models."
        )
        note.setWordWrap(True)
        form.addRow(note)
        self.validation_label = QLabel("")
        self.validation_label.setObjectName("validationError")
        self.validation_label.setWordWrap(True)
        self.validation_label.setStyleSheet("color: #9b1c1c; font-weight: bold;")
        form.addRow("Validation:", self.validation_label)
        return box

    @staticmethod
    def _input(default: str, object_name: str) -> QLineEdit:
        widget = QLineEdit(default)
        widget.setObjectName(object_name)
        return widget

    def _build_commands(self) -> QGroupBox:
        box = QGroupBox("Operator commands")
        layout = QGridLayout(box)
        actions: tuple[tuple[str, Callable[[], None], str], ...] = (
            ("Connect Simulation", self._connect, "connectButton"),
            ("Disconnect Simulation", self._disconnect, "disconnectButton"),
            ("Acquire Control Lease", self._acquire_lease, "acquireLeaseButton"),
            ("Renew Control Lease", self._renew_lease, "renewLeaseButton"),
            ("Release Control Lease", self._release_lease, "releaseLeaseButton"),
        )
        for index, (text, callback, name) in enumerate(actions):
            button = QPushButton(text)
            button.setObjectName(name)
            button.clicked.connect(callback)
            self._action_buttons[name] = button
            layout.addWidget(button, index // 3, index % 3)
        command_actions: tuple[tuple[CommandName, str, Callable[[], CommandPayload]], ...] = (
            (CommandName.ENABLE_SERVO, "Enable Simulated Servo", lambda: EnableServoPayload(True)),
            (
                CommandName.DISABLE_SERVO,
                "Disable Simulated Servo",
                lambda: DisableServoPayload(True),
            ),
            (CommandName.HOME, "Start Simulated PL-Reference Homing", self._home_payload),
            (CommandName.START_SINGLE_MOVE, "Start Simulated Single Move", self._move_payload),
            (CommandName.START_CYCLE, "Start Simulated Finite Cycle", self._cycle_payload),
            (CommandName.PAUSE, "Pause", PausePayload),
            (CommandName.RESUME, "Resume", lambda: ResumePayload(True)),
            (CommandName.CONTROLLED_STOP, "Controlled Stop", ControlledStopPayload),
            (CommandName.RESET_FAULT, "Reset Fault", lambda: ResetFaultPayload(True)),
        )
        offset = 2
        for index, (name, text, payload_factory) in enumerate(command_actions):
            button = QPushButton(text)
            button.setObjectName(f"command_{name.value}")
            button.clicked.connect(
                lambda checked=False, command=name, factory=payload_factory: self._submit(
                    command, factory
                )
            )
            self._command_buttons[name] = button
            layout.addWidget(button, offset + index // 3, index % 3)
        stop_note = QLabel("Controlled Stop is not a hardware emergency stop.")
        stop_note.setWordWrap(True)
        layout.addWidget(stop_note, offset + 3, 0, 1, 3)
        return box

    def _build_simulation_panel(self) -> QGroupBox:
        box = QGroupBox("Simulation / developer fault injection — simulation only")
        layout = QGridLayout(box)
        options = (
            ("Communication Loss", SimulationFault.COMMUNICATION_LOSS),
            ("Drive Fault", SimulationFault.DRIVE_FAULT),
            ("Arm PL Never Found", SimulationFault.PL_NEVER_FOUND),
            ("Arm Search Timeout", SimulationFault.HOMING_TIMEOUT),
            ("Arm PL Stuck Active", SimulationFault.PL_STUCK_ACTIVE),
            ("Arm Backoff Timeout", SimulationFault.BACKOFF_TIMEOUT),
            ("PL Active", SimulationFault.PL_ACTIVE),
            ("NL Active", SimulationFault.NL_ACTIVE),
            ("PL + NL Active", SimulationFault.PL_AND_NL_ACTIVE),
            ("Clear PL / NL", SimulationFault.CLEAR_LIMITS),
            ("Expire Control Lease", SimulationFault.CONTROL_LEASE_EXPIRY),
        )
        for index, (text, fault) in enumerate(options):
            button = QPushButton(text)
            button.setObjectName(f"inject_{fault.value}")
            button.clicked.connect(lambda checked=False, selected=fault: self._inject(selected))
            layout.addWidget(button, index // 3, index % 3)
        return box

    def _build_events(self) -> QGroupBox:
        box = QGroupBox("Recent events and errors (bounded to 100)")
        layout = QVBoxLayout(box)
        self.event_history = QTextEdit()
        self.event_history.setObjectName("eventHistory")
        self.event_history.setReadOnly(True)
        self.event_history.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.event_history)
        return box

    def _connect(self) -> None:
        self._show_action(self._client.connect())

    def _disconnect(self) -> None:
        self._show_action(self._client.disconnect())

    def _acquire_lease(self) -> None:
        self._show_action(self._client.acquire_lease())

    def _renew_lease(self) -> None:
        self._show_action(self._client.renew_lease())

    def _release_lease(self) -> None:
        self._show_action(self._client.release_lease())

    def _inject(self, fault: SimulationFault) -> None:
        self._show_action(self._client.inject_fault(fault))

    def _show_action(self, result: ClientActionResult) -> None:
        self.validation_label.setText("" if result.accepted else f"{result.code}: {result.message}")
        self.statusBar().showMessage(result.message, 5000)
        self.refresh_view()

    def _submit(self, name: CommandName, payload_factory: Callable[[], CommandPayload]) -> None:
        try:
            payload = payload_factory()
        except InputValidationError as exc:
            self.validation_label.setText(str(exc))
            return
        result = self._client.submit(name, payload)
        if result.error is None:
            self.validation_label.setText("")
            self.statusBar().showMessage(
                f"{name.value}: {result.status.value}; acceptance is not operation completion.",
                5000,
            )
        else:
            self.validation_label.setText(f"{result.error.code.value}: {result.error.message}")
        self.refresh_view()

    def _home_payload(self) -> HomePayload:
        return HomePayload(self._parse_int(self.homing_timeout_input, "Homing timeout", 1, 1000))

    def _move_payload(self) -> SingleMovePayload:
        return SingleMovePayload(
            position_units=self._parse_float(self.target_input, "Move target", -100.0, 100.0),
            speed_units_per_tick=self._parse_float(self.speed_input, "Speed", 0.000001, 100.0),
        )

    def _cycle_payload(self) -> CyclePayload:
        positive = self._parse_float(self.positive_input, "Positive target", -100.0, 100.0)
        negative = self._parse_float(self.negative_input, "Negative target", -100.0, 100.0)
        if positive <= negative:
            raise InputValidationError("Positive target must be greater than negative target.")
        return CyclePayload(
            positive_position_units=positive,
            negative_position_units=negative,
            speed_units_per_tick=self._parse_float(self.speed_input, "Speed", 0.000001, 100.0),
            cycle_count=self._parse_int(self.cycle_count_input, "Cycle count", 1, 10),
        )

    @staticmethod
    def _parse_float(widget: QLineEdit, title: str, minimum: float, maximum: float) -> float:
        try:
            number = float(widget.text())
        except ValueError as exc:
            raise InputValidationError(f"{title} must be a number.") from exc
        if not math.isfinite(number) or not minimum <= number <= maximum:
            raise InputValidationError(f"{title} must be between {minimum:g} and {maximum:g}.")
        return number

    @staticmethod
    def _parse_int(widget: QLineEdit, title: str, minimum: int, maximum: int) -> int:
        text = widget.text().strip()
        try:
            number = int(text)
        except ValueError as exc:
            raise InputValidationError(f"{title} must be a whole number.") from exc
        if str(number) != text and str(number) != text.lstrip("+"):
            raise InputValidationError(f"{title} must be a whole number.")
        if not minimum <= number <= maximum:
            raise InputValidationError(f"{title} must be between {minimum} and {maximum}.")
        return number

    def _authorization_payloads(self) -> dict[CommandName, CommandPayload]:
        payloads: dict[CommandName, CommandPayload] = {
            CommandName.ENABLE_SERVO: EnableServoPayload(True),
            CommandName.DISABLE_SERVO: DisableServoPayload(True),
            CommandName.HOME: HomePayload(20),
            CommandName.PAUSE: PausePayload(),
            CommandName.RESUME: ResumePayload(True),
            CommandName.CONTROLLED_STOP: ControlledStopPayload(),
            CommandName.RESET_FAULT: ResetFaultPayload(True),
        }
        try:
            payloads[CommandName.START_SINGLE_MOVE] = self._move_payload()
        except InputValidationError:
            pass
        try:
            payloads[CommandName.START_CYCLE] = self._cycle_payload()
        except InputValidationError:
            pass
        return payloads

    def refresh_view(self) -> None:
        payloads = self._authorization_payloads()
        authorizations = {
            name: self._client.authorize(name, payload) for name, payload in payloads.items()
        }
        view = present(
            self._client.state(),
            self._client.telemetry(),
            self._client.lease(),
            self._client.completed_cycles(),
            authorizations,
        )
        self._apply_view(view)
        self._append_events()

    def _apply_view(self, view: MainView) -> None:
        for key in self._state_labels:
            label = self._state_labels[key]
            text = getattr(view, key)
            label.setText(text)
            label.setStyleSheet(self._status_style(text))
        for key in self._telemetry_labels:
            self._telemetry_labels[key].setText(getattr(view.telemetry, key))
        for name, button in self._command_buttons.items():
            button.setEnabled(view.command_enabled.get(name, False))
        lease = self._client.lease()
        state = self._client.state()
        self._action_buttons["connectButton"].setEnabled(
            state.connection.value in {"DISCONNECTED", "COMMUNICATION_FAULT"}
        )
        self._action_buttons["disconnectButton"].setEnabled(
            state.connection.value != "DISCONNECTED"
        )
        self._action_buttons["acquireLeaseButton"].setEnabled(not lease.active)
        self._action_buttons["renewLeaseButton"].setEnabled(lease.active)
        self._action_buttons["releaseLeaseButton"].setEnabled(lease.active)

    @staticmethod
    def _status_style(text: str) -> str:
        if "[FAULT]" in text or "[BLOCKED]" in text:
            return "color: #9b1c1c; font-weight: bold;"
        if "[ACTIVE]" in text or "[PAUSED]" in text or "[STOPPING]" in text:
            return "color: #7a3e00; font-weight: bold;"
        if "[OK]" in text or "[CLEAR]" in text or "[PERMITTED]" in text:
            return "color: #176b2c; font-weight: bold;"
        return "color: #374151; font-weight: bold;"

    def _append_events(self) -> None:
        for event in self._client.events():
            if event.sequence > self._last_event_sequence:
                self.event_history.append(
                    f"{event.sequence:04d} [{event.category}] {event.message}"
                )
                self._last_event_sequence = event.sequence

    def _on_tick(self) -> None:
        self._client.advance(1)
        self.refresh_view()

    @property
    def simulation_timer_active(self) -> bool:
        return self._timer.isActive()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._timer.stop()
        self._client.shutdown()
        event.accept()
