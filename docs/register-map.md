# A6-RS documentary register catalog and codec assumptions

This is design evidence for the future Raspberry Pi motion service. Milestone 4 composes
the pure codec/catalog with an offline fake transport and symbolic read-only reader. The
Windows GUI must never use this map or access registers. Milestone 7 adds only a manually
invoked, Pi-only, one-shot diagnostic for three U16 symbols. Future operator API operations remain high-level and allowlisted;
this table must not be exposed as a general-purpose register interface.

All entries must be verified against the supplied A6-RS parameter-list PDF and the exact
installed firmware. Numeric notation is retained from the historical project map; some
entries occur in legacy Python, others only in current repository documentation. See the
[evidence matrix](evidence-matrix.md) for per-field provenance, every current
15-entry catalog item, communication gaps and the dedicated address comparison.

The historical-code communication baseline is Modbus RTU, slave 1, 9600 baud, 8 data bits,
no parity, 1 stop bit, and a 1 second host timeout, not a confirmed current configuration.
Legacy MinimalModbus code used
`BYTEORDER_LITTLE` for 32-bit values. The new family manual establishes high-byte-first
inside each word and selectable low/high word order for C parameters, but the installed
C0A.06 setting remains unverified. No persistent register is written at startup or reconnect.

The supplied parameter-list communication table (PDF pp. 36–37, printed 276–277) documents
C0A.06 selectable
word order: 0 low 16 bits first (default), 1 high 16 bits first. It does not establish the
installed setting. The Milestone 6 Chapter 9 excerpt documents high byte then low byte in
each 16-bit word, FC03 for parameter reads and group/suffix bytes as the PDU address,
with no +/-1 adjustment. Its default baud is 115200, while legacy code selected 9600.
Together with the U16/RO parameter-list entries, this supports FC03 addresses `0x4004`,
`0x4108`, and `0x410A` for the narrow diagnostic. Installed model/firmware/settings and
genuine captures remain unresolved. Gate B is prepared/conditional; Gates C/D remain
blocked. The [commissioning procedure](read-only-commissioning.md) is not permission to
read.

## Primitive and layout model

The codec supports strict `U16`, `I16`, `U32`, and `I32` values with their standard
numeric ranges and signed two's-complement representation. It rejects booleans,
non-integers, out-of-range values, invalid 16-bit words, and wrong word counts without
truncation, wrapping, clipping, saturation, or implicit rounding.

`ByteOrder.BIG` and `ByteOrder.LITTLE` describe byte order inside each 16-bit word.
`WordOrder.HIGH_WORD_FIRST` and `WordOrder.LOW_WORD_FIRST` describe the ordering of two
words. All four 32-bit combinations are supported, but every call requires an explicit
layout. None is a verified hardware default. The legacy MinimalModbus
`BYTEORDER_LITTLE` setting remains historical evidence only because that single name does
not independently identify byte and word order.

## Address notation

Manual labels such as `C11.06` and `U41.0A`, parameter group/index notation, numeric
runtime addresses, and transport-library addresses are distinct. Catalog numeric values
preserve the historical project map exactly. The codec neither derives an address from a
manual label nor adds or subtracts one. For documented C parameters, direct PDU
group/offset mapping is supported with no one-based adjustment. The three selected U16
monitor symbols use the same documented parameter rule. MinimalModbus conventions remain
historical; no adapter may introduce an automatic offset.

The metadata string "historical zero-based runtime address" remains historical. The three
diagnostic entries explicitly identify FC03 parameter area and direct group/offset PDU
addresses. Object-style homing notation must not be converted to RTU addresses without
evidence.

## Evidence and verification states

- `MANUAL_CONFIRMED`: supplied-manual evidence, not physical-drive confirmation.
- `LEGACY_CODE_ONLY`: recorded only in immutable legacy evidence.
- `MANUAL_AND_LEGACY_AGREE`: both documentary sources agree.
- `AMBIGUOUS`: documentary sources conflict or are incomplete.
- `HARDWARE_VERIFICATION_REQUIRED`: metadata requires exact-drive confirmation.

Most catalog entries use `HARDWARE_VERIFICATION_REQUIRED`, principally because installed
applicability and active 32-bit word order have not been verified. The three one-word
diagnostic entries are `MANUAL_CONFIRMED`, which does not imply current hardware verification.
`U40.01` is explicitly
ambiguous: the manual table identifies I16 while nearby prose calls it a 32-bit integer.

Exact scale metadata uses rational values: temperatures and bus voltage use `1/10`,
torque uses `1/10` percent rated torque, and application units use `1`. Raw decoding is
separate from physical scaling. Application units are never joint degrees, and historical
electronic gearing 9/16384 is not a joint calibration.

## Catalog policy

### Milestone 4 read policy

The immutable operational read allowlist contains `SERVO_STATUS`, `POSITION_FEEDBACK`,
`SPEED_FEEDBACK`, `TORQUE_FEEDBACK`, `BUS_VOLTAGE`, `POSITION_DEVIATION`,
`MOTOR_TEMPERATURE`, `ENCODER_TEMPERATURE`, `PLAN_OPERATION_GROUP`, and `DI_STATUS`.

The separate engineering inspection allowlist contains `POSITION_REFERENCE_SELECTION`,
`GEAR_1_NUMERATOR`, `GEAR_1_DENOMINATOR`, and `PLAN_MODE`. Engineering permission is
strictly boolean and disabled by default; granting it never enables writing. The catalog's
`GROUP_1_DISPLACEMENT` belongs to neither read allowlist. Snapshot assembly is operational
only, even when engineering inspection is enabled. Unknown symbols and unresolved
addresses fail closed. Reader callers cannot supply addresses, offsets, or function codes.

Except for the three Milestone 7 U16 diagnostic entries, catalog areas/function-code
mappings remain `UNRESOLVED`. The offline reader's supported override is explicit
`OfflineFixtureInterpretation` for the `synthetic-offline-fixture` source,
using area `OFFLINE_FIXTURE`. This does not establish a real register area or addressing
convention. No default hardware byte layout or address offset is inferred.

Each decoded result retains immutable raw words, actual requested address/count, original
catalog area, sequence, injected acquisition timestamps, exact scale metadata, source,
documentary verification and `HARDWARE_UNVERIFIED` layout status. Missing explicit 32-bit
fixture layouts raise `UnverifiedLayoutError`; successful fixture decoding is only
`FIXTURE_VALID`, never hardware-verified. Scaling remains metadata-only (no scaled physical
value or rounding), and application units never become joint degrees.

Ambiguous speed feedback returns the synthetic one-word table-form record but no decoded
scalar or selected layout. This does not resolve the conflicting 32-bit prose; its result
is `AMBIGUOUS` and the snapshot is degraded. No genuine raw capture is supplied or claimed;
test words are explicitly synthetic, including non-symmetric positive/negative patterns.

Snapshots default to the ten operational symbols, in deterministic sorted order. They
retain successful fields and explicit per-field error codes, marking overall validity
`DEGRADED` for any failure or ambiguity. A smaller non-ambiguous successful selection is
`FIXTURE_VALID`. Missing, stale or failed fields are never zero-filled or reused from a
cache. Freshness means fresh at acquisition; consumers must use monotonic acquisition time
to assess age later. Sequence numbers advance per transport attempt (gaps indicate failed
attempts); snapshots have a separate sequence. Calls do not retry or poll. With only
synchronous in-memory reads there is no pending task requiring cancellation.

The stable error hierarchy separates authorization, symbol/address/area resolution,
layout, codec decode, timeout/disconnection, checksum/protocol, short/extra response,
invalid word, unknown fixture and stale-data failures. Checksum errors are injected
outcomes only, not an RTU CRC implementation. Snapshot failure messages are bounded generic
diagnostics, never raw lower-layer exceptions. No failed read is reported as a drive fault.

**All register writes are prohibited and absent in Milestone 4.** Neither the reader nor
the transport has a write or generic execute method; these results cannot authorize motion.

Catalog inclusion is not access authorization. `REGISTER_CATALOG` is immutable and offers
only symbolic lookup/listing. There is no arbitrary read/write interface. Electronic
gearing, position-reference selection, planning configuration, displacements, DI/DO
assignment, and homing configuration are machine-defining or safety-relevant and require
a future disabled-by-default engineering workflow. This milestone implements no such
workflow and no register write.

### Broader historical design table — not the executable catalog or a read allowlist

The table below retains earlier design entries. Only the 15 entries audited in
evidence-matrix.md exist in the current executable catalog. Numeric values here are not
approved transport addresses, and documentary RW access does not authorize writes.

| Symbol | Address | Type | Scale/access | Meaning |
|---|---:|---|---|---|
| CONTROL_MODE | 0x0000 | U16 | RW, at stop | C00.00 |
| POSITION_REFERENCE_SELECTION | 0x0300 | U16 | RW, at stop | C03.00; 1 = internal planning |
| GEAR_1_NUMERATOR | 0x0302 | U32 | RW | C03.02 |
| GEAR_1_DENOMINATOR | 0x0304 | U32 | RW | C03.04 |
| GEAR_2_NUMERATOR | 0x0306 | U32 | RW | C03.06 |
| GEAR_2_DENOMINATOR | 0x0308 | U32 | RW | C03.08 |
| FAULT_RESET_LOGIC | 0x040D | U16 | RW | DI4 logic selection in legacy code |
| SERVO_ON_LOGIC | 0x0411 | U16 | RW | DI5 logic selection in legacy code |
| DI6_FUNCTION | 0x0414 | U16 | RW | Function 19 = position planning trigger |
| DI6_LOGIC | 0x0415 | U16 | RW | Virtual DI6 level/logic used by legacy code |
| DI7_FUNCTION | 0x0418 | U16 | RW | Function 20 = position planning pause |
| DI7_LOGIC | 0x0419 | U16 | RW | Virtual DI7 level/logic used by legacy code |
| PLAN_MODE | 0x1100 | U16 | RW, at stop | C11.00 |
| PLAN_REFERENCE_TYPE | 0x1101 | U16 | RW, at stop | C11.01; 1 = relative |
| PLAN_UPDATE_MODE | 0x1102 | U16 | RW, at stop | C11.02 |
| PLAN_INITIAL_GROUP | 0x1103 | U16 | RW, at stop | C11.03 |
| PLAN_END_GROUP | 0x1104 | U16 | RW, at stop | C11.04 |
| PLAN_REMAINING_SEGMENTS | 0x1105 | U16 | RW, at stop | C11.05 |
| GROUP_1_DISPLACEMENT | 0x1106 | I32 | application unit | C11.06 |
| GROUP_1_SPEED | 0x1108 | U16 | rpm | C11.08 |
| GROUP_1_ACCEL_TIME | 0x110A | U32 | ms | C11.0A |
| GROUP_1_DECEL_TIME | 0x110C | U32 | ms | C11.0C |
| GROUP_1_WAIT_TIME | 0x110E | U32 | ms | C11.0E |
| GROUP_2_DISPLACEMENT | 0x1110 | I32 | application unit | C11.10 |
| GROUP_2_SPEED | 0x1112 | U16 | rpm | C11.12 |
| GROUP_2_ACCEL_TIME | 0x1114 | U32 | ms | C11.14 |
| GROUP_2_DECEL_TIME | 0x1116 | U32 | ms | C11.16 |
| GROUP_2_WAIT_TIME | 0x1118 | U32 | ms | C11.18 |
| SPEED_FEEDBACK | 0x4001 | I16, ambiguous | rpm, RO | U40.01; table says I16; prose says 32-bit |
| TORQUE_FEEDBACK | 0x4003 | I16 | 0.1%, RO | U40.03 |
| DI_STATUS | 0x4004 | U16 | raw DI1-DI8 electrical levels, RO | U40.04 |
| BUS_VOLTAGE | 0x4006 | U16 | 0.1 V, RO | U40.06 |
| POSITION_DEVIATION | 0x4010 | I32 | encoder pulses, RO | U40.10 |
| POSITION_FEEDBACK | 0x4016 | I32 | application unit, RO | U40.16 |
| MOTOR_TEMPERATURE | 0x4031 | I16 | 0.1 deg C, RO | U40.31 |
| ENCODER_TEMPERATURE | 0x4032 | I16 | 0.1 deg C, RO | U40.32 |
| PLAN_OPERATION_GROUP | 0x4108 | U16 | RO | U41.08 |
| SERVO_STATUS | 0x410A | U16 | RO | 0 not ready, 1 ready, 2 running, 3 fault |

Groups 3 and 4 used by the legacy Jog code follow C11.20 and C11.30. Add them only
after verifying the intended Jog behavior and correcting the legacy forward-function typo.

Homing registers remain absent from the executable catalog until the exact model/firmware
manual, selected mode 18, PL/NL wiring, data types, units, and write conditions
have been verified.
Engineering parameter writes require Servo Off, explicit authorization, a logged reason,
backup, and read-back verification.
