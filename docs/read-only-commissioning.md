# One-shot read-only commissioning diagnostic

Safety level: **Controlled read-only commissioning preparation**. The diagnostic is for a
supervised Raspberry Pi session while the drive is confirmed Servo Disabled. It does not
authorize Servo On, Fault Reset, homing, motion, parameter changes, or repeated polling.

## Fixed scope

The CLI accepts only these symbolic read-only U16 parameters:

| Symbol | Manual parameter | PDU address | Intended observation |
|---|---:|---:|---|
| `SERVO_STATUS` | U41.0A | `0x410A` | Raw servo state; selected first read |
| `PLAN_OPERATION_GROUP` | U41.08 | `0x4108` | Raw current planning group |
| `DI_STATUS` | U40.04 | `0x4004` | Raw DI1-DI8 electrical levels |

The A6-RS communication manual states that parameters use FC03 and that the group and
offset form the address high and low bytes. The parameter list identifies all three as
U16/read-only. This supports a single documentary mapping; it does not verify the
installed drive, firmware, station, settings, wiring, input assignment, or active level.

The tool has no generic numeric-address option, discovery, slave/register/function scan,
write method, retry, polling loop, reconnect, background service, or simulation fallback.
It permits one request per armed invocation, validates slave/function/length/CRC, reports
stable structured errors and Modbus exceptions, records UTC and monotonic times plus raw
request/response bytes, and closes the serial port for success and failure.

## Local configuration

Create untracked `config/pi.local.toml` on the Pi. Record the exact stable path; do not use
`/dev/ttyUSB0` or commit the local value.

```toml
[serial]
device = "/dev/serial/by-id/REPLACE_WITH_OBSERVED_DEVICE"
slave_address = 1
baudrate = 9600
bytesize = 8
parity = "N"
stopbits = 1
timeout_s = 1.0
pl_input_number = 0
nl_input_number = 0
pl_active_level = "unverified"
nl_active_level = "unverified"
```

Numbers `1..8` may be entered only after the installed DI assignments are observed.
Active levels remain `unverified` until the installed electrical behavior is established.

## Commands

Preview and validate without opening a serial device:

```bash
python -m knee_rig.motion.diagnostics validate-config \
  --config config/pi.local.toml --register SERVO_STATUS
```

After completing Stop Points A and B, review the printed path, slave, FC, address, count,
timeout, and raw request. Obtain explicit authorization for that exact read, then invoke:

```bash
python -m knee_rig.motion.diagnostics read \
  --config config/pi.local.toml --register SERVO_STATUS \
  --arm-read-only-hardware
```

Run a later `DI_STATUS` invocation only after separate review/authorization for it:

```bash
python -m knee_rig.motion.diagnostics read \
  --config config/pi.local.toml --register DI_STATUS \
  --arm-read-only-hardware
```

No command in this document was run against hardware during Milestone 7.

## Stationary PL/NL observation

With the drive Servo Disabled and mechanism stationary, record one `DI_STATUS` result for
each supervised condition: neither switch actuated; PL manually actuated; PL released;
NL manually actuated; NL released. Do not move the mechanism under power to operate a
switch. Test simultaneous PL/NL contradiction in simulation only unless a qualified review
separately establishes that physical simultaneous actuation is safe.

The raw U16 value is always shown. When a configured input number is known but polarity is
not, its raw bit is labelled `ACTIVE_LEVEL_UNVERIFIED`; the output must not claim active or
inactive. Interpret PL/NL only after both bit assignment and active electrical level are
verified and recorded.

## Stop and close

Stop on unexpected motion/state, timeout, Modbus exception, malformed response, CRC,
slave/function/length mismatch, disconnect, contradictory evidence, unsafe condition,
loss of supervision, or authorization mismatch. Do not retry, probe an alternative, issue
a corrective command, reset the drive, change serial settings, or power-cycle as software
recovery. Preserve the output, close communication, and return to review. See the
[Session 1 checklist](lab-commissioning-session-1.md) and
[observation record](lab-observation-record.md).
