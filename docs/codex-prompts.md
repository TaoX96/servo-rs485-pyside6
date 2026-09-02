# Suggested prompts for future milestones

Give Codex one explicitly approved milestone at a time. Milestone 3 now provides a pure
register codec and documentary catalog; it does not authorize transport or hardware access.

## Completed Milestone 1 - contracts and simulation

Implemented components are strict typed configuration, shared API/state models, centralized
authorization, `ServoInterface`, deterministic `FakeServo`, an in-process coordinator,
and hardware-independent unit tests. There is still no network, GUI, monitoring, or real
driver implementation.

## Completed Milestone 2 - in-process simulation GUI

The minimal PySide6 shell communicates only through `MotionClient` and
`InProcessSimulationClient`. It presents state, telemetry, authorization, bounded command
inputs and events, lease behavior, and simulation-only faults without networking,
monitoring, serial transport, or hardware access.

## Completed Milestone 3 - transport-free register codec

Implemented components are pure U16, I16, U32, and I32 codecs, explicit byte and word
order, immutable register specifications, and a conservative read-only catalog. No
transport, hardware diagnostic, register I/O, or hardware operation was added.

## Milestone 4 - transport design and offline adapter tests

> Design the Pi-owned read-only transport boundary and test it only against a fake backend
> and recorded word fixtures. Keep 32-bit layout unverified, add no hardware test, perform
> no device discovery, and expose no writes, Servo On, homing, or motion.

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
