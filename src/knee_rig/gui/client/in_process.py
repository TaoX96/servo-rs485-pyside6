"""In-process adapter that is the GUI's only route to the simulation core."""

from __future__ import annotations

from collections import deque
from dataclasses import replace
from uuid import UUID, uuid4

from knee_rig.common.config import AppConfig, FeatureConfig, LimitsConfig
from knee_rig.common.config.models import MotionServiceConfig, default_config
from knee_rig.common.models import (
    AlarmInfo,
    AuthorizationDecision,
    CommandEnvelope,
    CommandName,
    CommandPayload,
    CommandResult,
    CommandStatus,
    ConnectionState,
    MotionState,
    StateSnapshot,
    TelemetrySnapshot,
)
from knee_rig.gui.client.interface import (
    ClientActionResult,
    ClientEvent,
    LeaseSnapshot,
    SimulationFault,
)
from knee_rig.motion.service import MotionCoordinator
from knee_rig.motion.simulation import FakeServo, HomingFailure, ManualClock
from knee_rig.motion.state_machine import AuthorizationContext, StateAuthorizer


def simulation_gui_config() -> AppConfig:
    """Return permissive simulation capabilities without authorizing angle motion."""
    return replace(
        default_config(),
        features=FeatureConfig(
            simulation=True,
            allow_servo_enable=True,
            allow_motion=True,
            allow_homing=True,
            allow_persistent_parameter_write=False,
            calibration_verified=False,
        ),
        limits=replace(LimitsConfig(), max_cycle_count=10),
        motion_service=MotionServiceConfig(control_lease_ttl_s=300.0),
    )


class InProcessSimulationClient:
    """Own deterministic simulation details and expose only high-level operations."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config if config is not None else simulation_gui_config()
        if not self._config.features.simulation:
            raise ValueError("InProcessSimulationClient requires simulation mode")
        self._clock = ManualClock()
        self._servo = FakeServo(clock=self._clock)
        self._coordinator = MotionCoordinator(self._config, self._servo)
        self._authorizer = StateAuthorizer()
        self._lease_id: UUID | None = None
        self._lease_deadline_s: float | None = None
        self._events: deque[ClientEvent] = deque(maxlen=100)
        self._event_sequence = 0
        self._last_state: StateSnapshot | None = None
        self._known_results: dict[UUID, CommandStatus] = {}
        self._coordinator.start()
        self._record(
            "lifecycle", "Simulation service started safely: disconnected, disabled, unhomed, idle."
        )
        self._capture_state_transition()

    def state(self) -> StateSnapshot:
        self._expire_if_due()
        return self._coordinator.state

    def telemetry(self) -> TelemetrySnapshot:
        return self._coordinator.telemetry()

    def alarms(self) -> tuple[AlarmInfo, ...]:
        return self._coordinator.alarms()

    def completed_cycles(self) -> int:
        return self._coordinator.completed_cycles

    def lease(self) -> LeaseSnapshot:
        self._expire_if_due()
        if self._lease_id is None or self._lease_deadline_s is None:
            return LeaseSnapshot(False)
        remaining = max(0.0, self._lease_deadline_s - self._clock.monotonic_s)
        return LeaseSnapshot(True, self._lease_id, remaining)

    def events(self) -> tuple[ClientEvent, ...]:
        return tuple(self._events)

    def connect(self) -> ClientActionResult:
        if self._coordinator.state.connection is ConnectionState.COMMUNICATION_FAULT:
            receipt = self._servo.reconnect_after_communication_fault()
            message = "Simulated communication restored; explicit fault reset is still required."
        else:
            receipt = self._coordinator.connect()
            message = "Simulation connected; servo remains disabled and unhomed."
        result = self._receipt(receipt.accepted, receipt.code, receipt.message, message)
        self._record_action("connection", result)
        self._capture_state_transition()
        return result

    def disconnect(self) -> ClientActionResult:
        receipt = self._coordinator.disconnect()
        self._lease_id = None
        self._lease_deadline_s = None
        result = self._receipt(
            receipt.accepted,
            receipt.code,
            receipt.message,
            "Simulation disconnected; lease cleared and no operation will resume automatically.",
        )
        self._record_action("connection", result)
        self._capture_state_transition()
        return result

    def acquire_lease(self) -> ClientActionResult:
        self._expire_if_due()
        candidate = uuid4()
        if not self._coordinator.acquire_control_lease(candidate):
            result = ClientActionResult(
                False, "LEASE_UNAVAILABLE", "A control lease is already active."
            )
        else:
            self._lease_id = candidate
            self._lease_deadline_s = self._clock.monotonic_s + self._lease_ttl_s
            result = ClientActionResult(
                True, "LEASE_ACQUIRED", "Simulation control lease acquired."
            )
        self._record_action("lease", result)
        return result

    def renew_lease(self) -> ClientActionResult:
        self._expire_if_due()
        if self._lease_id is None:
            result = ClientActionResult(False, "LEASE_REQUIRED", "No active lease can be renewed.")
        else:
            self._lease_deadline_s = self._clock.monotonic_s + self._lease_ttl_s
            result = ClientActionResult(True, "LEASE_RENEWED", "Simulation control lease renewed.")
        self._record_action("lease", result)
        return result

    def release_lease(self) -> ClientActionResult:
        self._expire_if_due()
        lease_id = self._lease_id
        if lease_id is None:
            result = ClientActionResult(False, "LEASE_REQUIRED", "No active lease can be released.")
        elif self._coordinator.release_control_lease(lease_id):
            self._lease_id = None
            self._lease_deadline_s = None
            result = ClientActionResult(
                True, "LEASE_RELEASED", "Simulation control lease released."
            )
        else:
            result = ClientActionResult(
                False, "LEASE_RELEASE_FAILED", "Lease release was rejected."
            )
        self._record_action("lease", result)
        self._capture_state_transition()
        return result

    def authorize(self, name: CommandName, payload: CommandPayload) -> AuthorizationDecision:
        self._expire_if_due()
        command = CommandEnvelope(uuid4(), name, payload)
        context = AuthorizationContext(
            control_lease_active=self._lease_id is not None,
            current_position_units=self._coordinator.telemetry().position_units,
        )
        return self._authorizer.authorize(command, self._coordinator.state, self._config, context)

    def submit(
        self,
        name: CommandName,
        payload: CommandPayload,
        *,
        command_id: UUID | None = None,
    ) -> CommandResult:
        self._expire_if_due()
        command = CommandEnvelope(command_id or uuid4(), name, payload)
        result = self._coordinator.handle(command, lease_id=self._lease_id)
        previous = self._known_results.get(command.command_id)
        if previous is None:
            self._known_results[command.command_id] = result.status
            self._record_command(result)
        self._capture_state_transition()
        return result

    def advance(self, ticks: int = 1) -> None:
        if ticks < 0:
            raise ValueError("ticks must not be negative")
        self._servo.advance(ticks)
        self._expire_if_due()
        self._coordinator.refresh()
        self._capture_command_completions()
        self._capture_state_transition()

    def inject_fault(self, fault: SimulationFault) -> ClientActionResult:
        if fault is SimulationFault.COMMUNICATION_LOSS:
            self._servo.inject_communication_fault()
            message = "Simulated communication loss injected."
        elif fault is SimulationFault.DRIVE_FAULT:
            self._servo.inject_drive_fault()
            message = "Simulated drive fault injected."
        elif fault is SimulationFault.HSW_NOT_FOUND:
            self._servo.set_next_homing_failure(HomingFailure.HSW_NOT_FOUND)
            message = "The next simulated homing operation is armed for HSW-not-found failure."
        elif fault is SimulationFault.HOMING_TIMEOUT:
            self._servo.set_next_homing_failure(HomingFailure.TIMEOUT)
            message = "The next simulated homing operation is armed to time out."
        elif fault is SimulationFault.PL_ACTIVE:
            limits = self._coordinator.state.limits
            self._servo.set_limits(pl_active=True, nl_active=False, hsw_active=limits.hsw_active)
            message = "Simulated PL input activated."
        elif fault is SimulationFault.NL_ACTIVE:
            limits = self._coordinator.state.limits
            self._servo.set_limits(pl_active=False, nl_active=True, hsw_active=limits.hsw_active)
            message = "Simulated NL input activated."
        elif fault is SimulationFault.PL_AND_NL_ACTIVE:
            limits = self._coordinator.state.limits
            self._servo.set_limits(pl_active=True, nl_active=True, hsw_active=limits.hsw_active)
            message = (
                "Contradictory simulated PL and NL inputs activated; explicit recovery is required."
            )
        elif fault is SimulationFault.CLEAR_LIMITS:
            limits = self._coordinator.state.limits
            self._servo.set_limits(pl_active=False, nl_active=False, hsw_active=limits.hsw_active)
            message = "Simulated PL and NL inputs cleared."
        else:
            self._coordinator.expire_control_lease()
            self._lease_id = None
            self._lease_deadline_s = None
            message = "Simulation control lease forcibly expired."
        result = ClientActionResult(True, "SIMULATION_INJECTION", message)
        self._record_action("simulation", result)
        self._coordinator.refresh()
        self._capture_command_completions()
        self._capture_state_transition()
        return result

    def shutdown(self) -> None:
        """Stop local progression and apply lease-loss policy without Servo Off."""
        state = self._coordinator.state
        if state.motion in {
            MotionState.STARTING,
            MotionState.MOVING,
            MotionState.PAUSED,
            MotionState.STOPPING,
        }:
            self._coordinator.expire_control_lease()
            self._lease_id = None
            self._lease_deadline_s = None
            self._servo.advance(1)
            self._coordinator.refresh()
            self._record(
                "shutdown",
                "GUI closed during motion; simulated lease-loss controlled stop requested.",
            )
        elif self._lease_id is not None:
            self._coordinator.release_control_lease(self._lease_id)
            self._lease_id = None
            self._lease_deadline_s = None
            self._record("shutdown", "GUI closed while idle; simulation lease released.")
        self._capture_command_completions()
        self._capture_state_transition()

    @property
    def _lease_ttl_s(self) -> float:
        return self._config.motion_service.control_lease_ttl_s

    def _expire_if_due(self) -> None:
        if self._lease_deadline_s is None or self._clock.monotonic_s < self._lease_deadline_s:
            return
        self._coordinator.expire_control_lease()
        self._lease_id = None
        self._lease_deadline_s = None
        self._record("lease", "Control lease expired; explicit reacquisition is required.")
        self._coordinator.refresh()
        self._capture_command_completions()
        self._capture_state_transition()

    @staticmethod
    def _receipt(
        accepted: bool,
        code: str | None,
        detail: str | None,
        success_message: str,
    ) -> ClientActionResult:
        return ClientActionResult(
            accepted,
            code or ("ACCEPTED" if accepted else "REJECTED"),
            success_message if accepted else detail or "The simulation action was rejected.",
        )

    def _record_action(self, category: str, result: ClientActionResult) -> None:
        outcome = "accepted" if result.accepted else "rejected"
        self._record(category, f"{outcome}: {result.code} — {result.message}")

    def _record_command(self, result: CommandResult) -> None:
        if result.error is None:
            message = (
                f"{result.name.value} accepted as {result.status.value}; ID {result.command_id}."
            )
        else:
            message = (
                f"{result.name.value} rejected: {result.error.code.value} — "
                f"{result.error.message}; ID {result.command_id}."
            )
        self._record("command", message)

    def _capture_command_completions(self) -> None:
        for command_id, previous in tuple(self._known_results.items()):
            result = self._coordinator.result_for(command_id)
            if result is None or result.status is previous:
                continue
            self._known_results[command_id] = result.status
            self._record(
                "command",
                f"{result.name.value} changed from {previous.value} to {result.status.value}; ID {command_id}.",
            )

    def _capture_state_transition(self) -> None:
        current = self._coordinator.state
        previous = self._last_state
        if previous is not None and current != previous:
            changes = []
            for name in ("service", "connection", "servo", "homing", "motion"):
                before = getattr(previous, name)
                after = getattr(current, name)
                if before is not after:
                    changes.append(f"{name}: {before.value} → {after.value}")
            if previous.active_fault_code != current.active_fault_code:
                changes.append(f"fault: {current.active_fault_code or 'none'}")
            if previous.recovery_required != current.recovery_required:
                changes.append(f"recovery required: {current.recovery_required}")
            if changes:
                self._record("state", "; ".join(changes))
        self._last_state = current

    def _record(self, category: str, message: str) -> None:
        self._event_sequence += 1
        self._events.append(ClientEvent(self._event_sequence, category, message))
