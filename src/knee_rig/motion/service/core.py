"""Small synchronous simulation core for serialized, idempotent command handling."""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import UUID

from knee_rig.common.config import AppConfig
from knee_rig.common.models import (
    AlarmInfo,
    CommandEnvelope,
    CommandError,
    CommandName,
    CommandResult,
    CommandStatus,
    ConnectionState,
    CyclePayload,
    DiagnosticValue,
    ErrorCode,
    HomePayload,
    HomingState,
    MotionState,
    ServiceState,
    ServoState,
    SingleMovePayload,
    StateSnapshot,
    TelemetrySnapshot,
)
from knee_rig.motion.driver import OperationReceipt, ServoInterface
from knee_rig.motion.state_machine import AuthorizationContext, StateAuthorizer


class MotionCoordinator:
    """Own one servo abstraction and serialize all simulation commands."""

    def __init__(
        self,
        config: AppConfig,
        servo: ServoInterface,
        *,
        authorizer: StateAuthorizer | None = None,
    ) -> None:
        if not config.features.simulation:
            raise ValueError("MotionCoordinator is simulation-only")
        self._config = config
        self._servo = servo
        self._authorizer = authorizer if authorizer is not None else StateAuthorizer()
        self._service_state = ServiceState.STOPPED
        self._lease_id: UUID | None = None
        self._recovery_required = False
        self._service_fault_code: str | None = None
        self._service_alarms: list[AlarmInfo] = []
        self._active_command_id: UUID | None = None
        self._pending_stop_command_id: UUID | None = None
        self._cancel_active_operation = False
        self._fingerprints: dict[UUID, str] = {}
        self._results: dict[UUID, CommandResult] = {}

    def start(self) -> None:
        """Start the in-process core without connecting or changing servo state."""
        if self._service_state is ServiceState.STOPPED:
            self._service_state = ServiceState.STARTING
            self._service_state = ServiceState.READY

    def stop(self) -> None:
        """Stop the simulation core and return the fake to its documented safe state."""
        self._service_state = ServiceState.STOPPING
        self._servo.disconnect()
        self._lease_id = None
        self._active_command_id = None
        self._pending_stop_command_id = None
        self._cancel_active_operation = False
        self._service_state = ServiceState.STOPPED

    def restart(self) -> None:
        """Reset tasks and authorization without automatic connection or recovery."""
        self.stop()
        self._fingerprints.clear()
        self._results.clear()
        self._recovery_required = False
        self._service_fault_code = None
        self._service_alarms.clear()
        self.start()

    def connect(self) -> OperationReceipt:
        if self._service_state is not ServiceState.READY:
            return OperationReceipt(False, False, "SERVICE_NOT_READY", "Start the core first.")
        receipt = self._servo.connect()
        self.refresh()
        return receipt

    def disconnect(self) -> OperationReceipt:
        receipt = self._servo.disconnect()
        self._lease_id = None
        self._fail_active_command()
        self.refresh()
        return receipt

    def acquire_control_lease(self, lease_id: UUID) -> bool:
        if self._lease_id is not None or self._service_state in {
            ServiceState.STARTING,
            ServiceState.STOPPING,
            ServiceState.STOPPED,
        }:
            return False
        self._lease_id = lease_id
        return True

    def release_control_lease(self, lease_id: UUID) -> bool:
        if self._lease_id != lease_id:
            return False
        if self._active_command_id is not None:
            self.expire_control_lease()
        else:
            self._lease_id = None
        return True

    def expire_control_lease(self) -> None:
        """Apply the documented software response; this is not an emergency stop."""
        self._lease_id = None
        state = self.state
        if self._active_command_id is not None or state.motion in {
            MotionState.STARTING,
            MotionState.MOVING,
            MotionState.PAUSED,
            MotionState.STOPPING,
        }:
            receipt = self._servo.request_controlled_stop()
            if receipt.accepted:
                code = "CONTROL_LEASE_EXPIRED"
                message = "Control lease expired; a simulated controlled stop was requested."
                self._cancel_active_operation = True
            else:
                code = "CONTROL_LEASE_EXPIRED_STOP_UNCONFIRMED"
                message = (
                    "Control lease expired while communication was unavailable; "
                    "software cannot guarantee a controlled stop."
                )
                self._fail_active_command()
            self._enter_service_fault(code, message)

    @property
    def state(self) -> StateSnapshot:
        servo_status = self._servo.read_status()
        service = self._service_state
        if service not in {ServiceState.STARTING, ServiceState.STOPPING, ServiceState.STOPPED} and (
            self._service_fault_code is not None
            or servo_status.active_fault_code is not None
            or servo_status.connection is ConnectionState.COMMUNICATION_FAULT
            or servo_status.servo is ServoState.SERVO_FAULT
            or servo_status.homing is HomingState.HOMING_FAULT
            or servo_status.motion is MotionState.MOTION_FAULT
        ):
            service = ServiceState.FAULT
        return StateSnapshot(
            service=service,
            connection=servo_status.connection,
            servo=servo_status.servo,
            homing=servo_status.homing,
            motion=servo_status.motion,
            limits=servo_status.limits,
            active_fault_code=self._service_fault_code or servo_status.active_fault_code,
            active_command_id=self._active_command_id,
            recovery_required=self._recovery_required or servo_status.active_fault_code is not None,
        )

    @property
    def completed_cycles(self) -> int:
        return self._servo.completed_cycles

    def telemetry(self) -> TelemetrySnapshot:
        return self._servo.read_telemetry()

    def alarms(self) -> tuple[AlarmInfo, ...]:
        return (*self._servo.read_alarms(), *self._service_alarms)

    def result_for(self, command_id: UUID) -> CommandResult | None:
        self.refresh()
        return self._results.get(command_id)

    def handle(self, command: CommandEnvelope, *, lease_id: UUID | None) -> CommandResult:
        """Synchronously accept/reject one command; long operations complete through ticks."""
        self.refresh()
        fingerprint = json.dumps(command.to_dict(), sort_keys=True, separators=(",", ":"))
        previous_fingerprint = self._fingerprints.get(command.command_id)
        if previous_fingerprint is not None:
            if previous_fingerprint == fingerprint:
                return self._results[command.command_id]
            return self._error_result(
                command,
                ErrorCode.COMMAND_ID_CONFLICT,
                "The command ID was already used with a different payload.",
            )

        context = AuthorizationContext(
            control_lease_active=lease_id is not None and lease_id == self._lease_id,
            current_position_units=self.telemetry().position_units,
        )
        decision = self._authorizer.authorize(command, self.state, self._config, context)
        if not decision.allowed:
            assert decision.failure is not None
            result = self._error_result(
                command,
                decision.failure.code,
                decision.failure.message,
                retryable=decision.failure.retryable,
                details=decision.failure.details,
            )
            self._remember(command, fingerprint, result)
            return result

        receipt = self._dispatch(command)
        if not receipt.accepted:
            code = (
                ErrorCode.COMMUNICATION_FAILURE
                if receipt.code in {"COMMUNICATION_FAILURE", "NOT_CONNECTED"}
                else ErrorCode.INTERNAL_ERROR
            )
            result = self._error_result(
                command,
                code,
                receipt.message or "The simulated servo rejected an authorized request.",
                details={"servo_code": receipt.code},
            )
            self._remember(command, fingerprint, result)
            return result

        is_primary_operation = command.name in {
            CommandName.HOME,
            CommandName.START_SINGLE_MOVE,
            CommandName.START_CYCLE,
        }
        if is_primary_operation and not receipt.completed:
            self._active_command_id = command.command_id
        if command.name is CommandName.CONTROLLED_STOP and not receipt.completed:
            self._pending_stop_command_id = command.command_id
            self._cancel_active_operation = True

        result = CommandResult(
            command_id=command.command_id,
            name=command.name,
            status=CommandStatus.SUCCEEDED if receipt.completed else CommandStatus.RUNNING,
            state=self.state,
        )
        self._remember(command, fingerprint, result)
        return result

    def refresh(self) -> None:
        """Observe fake progress and finalize recorded results without blocking."""
        state = self.state
        if state.connection is ConnectionState.COMMUNICATION_FAULT:
            self._recovery_required = True
            if self._service_fault_code is None:
                if state.motion is MotionState.MOTION_FAULT:
                    self._enter_service_fault(
                        "COMMUNICATION_FAULT_STOP_UNCONFIRMED",
                        "Communication was lost during an active operation; software cannot "
                        "confirm a controlled stop.",
                    )
                else:
                    self._service_fault_code = "COMMUNICATION_FAULT"

        active_id = self._active_command_id
        if active_id is not None:
            if self._cancel_active_operation and state.motion is MotionState.IDLE:
                self._update_result(active_id, CommandStatus.CANCELLED)
                self._active_command_id = None
                self._cancel_active_operation = False
            elif state.has_blocking_fault and state.motion is not MotionState.STOPPING:
                self._update_result(active_id, CommandStatus.FAILED)
                self._active_command_id = None
            elif state.homing is not HomingState.HOMING and state.motion is MotionState.IDLE:
                status = (
                    CommandStatus.CANCELLED
                    if self._cancel_active_operation
                    else CommandStatus.SUCCEEDED
                )
                self._update_result(active_id, status)
                self._active_command_id = None
                self._cancel_active_operation = False

        stop_id = self._pending_stop_command_id
        if stop_id is not None and state.motion is MotionState.IDLE:
            self._update_result(stop_id, CommandStatus.SUCCEEDED)
            self._pending_stop_command_id = None

    def _dispatch(self, command: CommandEnvelope) -> OperationReceipt:
        payload = command.payload
        if command.name is CommandName.ENABLE_SERVO:
            return self._servo.request_servo_enable()
        if command.name is CommandName.DISABLE_SERVO:
            return self._servo.request_servo_disable()
        if command.name is CommandName.HOME:
            assert isinstance(payload, HomePayload)
            return self._servo.request_homing(timeout_ticks=payload.timeout_ticks)
        if command.name is CommandName.START_SINGLE_MOVE:
            assert isinstance(payload, SingleMovePayload)
            position_units = payload.position_units
            if position_units is None:
                assert payload.joint_angle_deg is not None
                position_units = self._config.calibration.position_units_for_angle(
                    payload.joint_angle_deg
                )
            return self._servo.start_single_move(
                position_units=position_units,
                speed_units_per_tick=payload.speed_units_per_tick,
            )
        if command.name is CommandName.START_CYCLE:
            assert isinstance(payload, CyclePayload)
            return self._servo.start_cycle(
                positive_position_units=payload.positive_position_units,
                negative_position_units=payload.negative_position_units,
                speed_units_per_tick=payload.speed_units_per_tick,
                cycle_count=payload.cycle_count,
            )
        if command.name is CommandName.PAUSE:
            return self._servo.pause()
        if command.name is CommandName.RESUME:
            return self._servo.resume()
        if command.name is CommandName.CONTROLLED_STOP:
            return self._servo.request_controlled_stop()
        if command.name is CommandName.RESET_FAULT:
            if self._servo.read_status().active_fault_code is None:
                receipt = OperationReceipt(True, True)
            else:
                receipt = self._servo.reset_fault()
            if receipt.accepted:
                self._service_state = ServiceState.READY
                self._service_fault_code = None
                self._recovery_required = False
                self._service_alarms = [
                    replace(alarm, active=False) for alarm in self._service_alarms
                ]
            return receipt
        raise AssertionError(f"Unhandled allowlisted command: {command.name}")

    def _remember(
        self,
        command: CommandEnvelope,
        fingerprint: str,
        result: CommandResult,
    ) -> None:
        self._fingerprints[command.command_id] = fingerprint
        self._results[command.command_id] = result

    def _error_result(
        self,
        command: CommandEnvelope,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, DiagnosticValue] | None = None,
    ) -> CommandResult:
        state = self.state
        error = CommandError(
            code=code,
            message=message,
            command_id=command.command_id,
            state=state,
            retryable=retryable,
            details=details if details is not None else {},
        )
        return CommandResult(
            command_id=command.command_id,
            name=command.name,
            status=CommandStatus.REJECTED,
            state=state,
            error=error,
        )

    def _update_result(self, command_id: UUID, status: CommandStatus) -> None:
        previous = self._results.get(command_id)
        if previous is not None:
            self._results[command_id] = replace(previous, status=status, state=self.state)

    def _fail_active_command(self) -> None:
        if self._active_command_id is not None:
            self._update_result(self._active_command_id, CommandStatus.FAILED)
            self._active_command_id = None
        self._pending_stop_command_id = None
        self._cancel_active_operation = False

    def _enter_service_fault(self, code: str, message: str) -> None:
        self._service_state = ServiceState.FAULT
        self._service_fault_code = code
        self._recovery_required = True
        occurred_at = self.telemetry().acquisition_time
        self._service_alarms.append(AlarmInfo(code, message, occurred_at))
