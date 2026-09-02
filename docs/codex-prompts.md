# Suggested prompts for future milestones

Give Codex one explicitly approved milestone at a time. Milestone 1 now provides the
simulation-only foundation; it does not authorize Milestone 2 or hardware access.

## Completed Milestone 1 - contracts and simulation

Implemented components are strict typed configuration, shared API/state models, centralized
authorization, `ServoInterface`, deterministic `FakeServo`, an in-process coordinator,
and hardware-independent unit tests. There is still no network, GUI, monitoring, or real
driver implementation.

## Milestone 2 - local service and GUI simulation

> Build a local in-process application/service composition around the existing simulation
> core and add a minimal PySide6 status shell that communicates only through a client
> abstraction. Keep networking fake or in-process; do not start HTTP/WebSocket, import a
> real serial transport, access hardware, or add monitoring implementation. Preserve all
> existing authorization, idempotency, restart, and lease-expiry tests.

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
