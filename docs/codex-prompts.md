# Suggested prompts for future milestones

Give Codex one explicitly approved milestone at a time. Milestone 7 prepares a supervised
read-only laboratory session; it does not authorize hardware access or motion by itself.

## Completed Milestone 1 - contracts and simulation

Implemented components are strict typed configuration, shared API/state models, centralized
authorization, `ServoInterface`, deterministic `FakeServo`, an in-process coordinator,
and hardware-independent unit tests. At that milestone there was no network, GUI,
monitoring, or real driver implementation; Milestone 2 subsequently added the simulation GUI.

## Completed Milestone 2 - in-process simulation GUI

The minimal PySide6 shell communicates only through `MotionClient` and
`InProcessSimulationClient`. It presents state, telemetry, authorization, bounded command
inputs and events, lease behavior, and simulation-only faults without networking,
monitoring, serial transport, or hardware access.

## Completed Milestone 3 - transport-free register codec

Implemented components are pure U16, I16, U32, and I32 codecs, explicit byte and word
order, immutable register specifications, and a conservative read-only catalog. No
transport, hardware diagnostic, register I/O, or hardware operation was added.

## Completed Milestone 4 - offline read-only transport boundary

Implemented components are a read-only protocol, deterministic synthetic-word transport,
immutable operational/engineering allowlists, symbolic reader, raw/decoded result metadata,
and bounded partial snapshots. Area/function-code mapping and 32-bit hardware layout stay
unverified. There is no real adapter, device discovery, write path, or GUI integration.

## Completed Milestone 5 - hardware readiness and evidence audit

Documentation-only evidence analysis covers the seven protected sources, all 14 current
catalog entries, hardware identity, communication/address/layout gaps and genuine-capture
absence. Gate A passes; B/C/D remain blocked. See [evidence](evidence-matrix.md),
[readiness](hardware-readiness.md) and the [future commissioning design](read-only-commissioning.md).
No code, tests, dependencies or configuration changed; no real adapter/skeleton, device
enumeration, hardware access or new physical verification was introduced.

## Completed Milestone 6 - evidence intake and Gate B reassessment

Five immutable local PDFs were manifested and reviewed. The A6-RS chapter documents FC03
and direct group/offset PDU addressing for C parameters; U-monitor mapping and installed
identity/settings/wiring remain unresolved. Gate B remains blocked and no first read is
approved. No code, device or network access was introduced.

## Completed Milestone 7 - laboratory commissioning preparation

Implemented a Pi-only one-shot FC03 diagnostic restricted to `SERVO_STATUS`,
`PLAN_OPERATION_GROUP`, and `DI_STATUS`, with config-only preview, exact by-id path,
explicit arming, raw-frame/timing/error reporting, zero retry, and guaranteed close. It is
isolated from GUI startup. Added Session 1 machine checklists and deterministic
`POSITIVE_LIMIT_REFERENCE` simulation with explicit search, controlled-stop, backoff,
offset, verification, and fault phases. No hardware was accessed; no writes or real
motion path were added.

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
