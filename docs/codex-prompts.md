# Suggested prompts for future milestones

Give Codex one explicitly approved milestone at a time. Milestone 0 defines architecture
and documentation only; it does not authorize Milestone 1 or hardware access.

## Milestone 1 - contracts and simulation

> Read the root AGENTS.md and all project documents. Implement hardware-independent typed
> configuration loading, shared API/state models, motion-state authorization, a simulated
> motion service, and tests. Keep every hardware gate disabled. Do not import or implement
> MinimalModbus/pyserial transport, open ports, access the Pi, enable, home, or move. Run
> applicable Ruff, mypy, and pytest checks and report exact results.

## Milestone 2 - local service and GUI simulation

> Implement the local simulated `/v1` API contract, command idempotency, controller lease,
> and a PySide6 shell that communicates only with that API. Test lease expiry, controlled
> stop to FAULT, restart-safe state, and monitoring isolation with fakes. Do not add a real
> serial transport or execute hardware actions.

## Milestone 3 - register codec and read-only Pi transport

> After model/firmware and protocol review, implement and test U16, I16, U32, and I32
> codecs with explicit configurable 32-bit order. Put a MinimalModbus transport only in
> the Pi motion-driver boundary and expose read-only status/telemetry initially. Add a
> hardware-marked diagnostic under tests/hardware, but do not run it without explicit
> authorization. Do not implement writes, Servo On, homing, or motion.

## Milestone 4 - isolated monitoring

> Implement the Pi monitoring service and Windows monitoring client with fake camera,
> temperature, and media backends. Verify that crashes, timeouts, storage errors, and
> cancellation cannot import, call, restart, or alter the motion service. Do not access
> real Pi hardware unless separately authorized.

## Later commissioning milestones

Calibration, engineering parameter setup, real homing, and real motion each require their
own reviewed milestone. Before proposing any of them, confirm the hardware inventory,
qualified electrical safety review, physical E-stop/STO/enable and PL/NL installation,
exact drive/firmware, register encoding, and bounded low-energy test procedure. Do not
combine approval to design a workflow with approval to execute it.

## Request template

> Goal: ...
> Allowed files and interfaces: ...
> Safety level: documentation only / simulation / read-only hardware / reviewed motion
> Exact hardware access authorized, if any: ...
> Acceptance criteria: ...
> Required checks: ...

Avoid broad requests such as “finish the application” or “make the servo run.” Never infer
hardware authorization from a software implementation request.

