# A6-RS register map used by this project

This is design evidence for the future Raspberry Pi motion service. The Windows GUI must
never use this map, open RS485, or read or write these registers. No register access exists
through Milestone 1. Future operator API operations remain high-level and allowlisted;
this table must not be exposed as a general-purpose register interface.

All entries must be verified against the supplied A6-RS parameter-list PDF and the exact
installed firmware. Address notation follows the historical Python test code.

The communication baseline is Modbus RTU, slave 1, 9600 baud, 8 data bits, no parity,
1 stop bit, and a 1 second timeout. Legacy MinimalModbus code used
`BYTEORDER_LITTLE` for 32-bit values, but byte and word order remain unverified for the
target drive and firmware. No persistent register is written at startup or reconnection.

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
| SPEED_FEEDBACK | 0x4001 | verify | rpm, RO | U40.01; manual width needs device verification |
| TORQUE_FEEDBACK | 0x4003 | I16 | 0.1%, RO | U40.03 |
| BUS_VOLTAGE | 0x4006 | U16 | 0.1 V, RO | U40.06 |
| POSITION_DEVIATION | 0x4010 | I32 | encoder pulses, RO | U40.10 |
| POSITION_FEEDBACK | 0x4016 | I32 | application unit, RO | U40.16 |
| MOTOR_TEMPERATURE | 0x4031 | I16 | 0.1 deg C, RO | U40.31 |
| ENCODER_TEMPERATURE | 0x4032 | I16 | 0.1 deg C, RO | U40.32 |
| PLAN_OPERATION_GROUP | 0x4108 | U16 | RO | U41.08 |
| SERVO_STATUS | 0x410A | U16 | RO | 0 not ready, 1 ready, 2 running, 3 fault |

Groups 3 and 4 used by the legacy Jog code follow C11.20 and C11.30. Add them only
after verifying the intended Jog behavior and correcting the legacy forward-function typo.

Homing registers are intentionally absent until the exact model/firmware manual, selected
homing mode, HSW/PL/NL wiring, data types, units, and write conditions have been verified.
Engineering parameter writes require Servo Off, explicit authorization, a logged reason,
backup, and read-back verification.
