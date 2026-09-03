# Laboratory observation record - session 1

Use one copy per attended session. Write `unknown` rather than inferring a value. Shared
records omit credentials and full serial numbers. Attach original raw JSON separately and
identify it by a controlled filename and SHA-256.

## Session and authorization

| Field | Record |
|---|---|
| Date, start/end UTC | |
| Operator and qualified reviewer | |
| Approved procedure revision | |
| Exact finite request list | |
| Explicit approval before each physical read | |
| Stop/close procedure reviewed | |

## Stop Point A - de-energized evidence

| Field | Record / evidence source |
|---|---|
| Drive model; redacted identity; firmware | |
| Motor model; brake option | |
| Adapter model/revision | |
| RS485 A/B/GND-reference terminals and continuity record | |
| Termination, bias, shielding, grounding, cable route | |
| PL mounting, terminal, contact type, assigned DI | |
| NL mounting, terminal, contact type, assigned DI | |
| Servo Enable/STO removal method and reviewer | |
| Mechanical restraint, gravity/brake assessment, clear area | |
| Station/baud/data/parity/stops/response delay source | |
| Sanitized `/dev/serial/by-id/...` identity reference | |
| Stop Point A reviewer decision | PASS / STOP |

## Stop Point B - powered but Servo Disabled

Independent Servo Disabled evidence: ____________________

Drive display/alarm observation: ____________________

Configured request timeout: ______ s. Automatic retries: **0**.

| Sequence | Condition / symbol | Planned request hex | Response hex / capture ID | CRC | Raw U16 | Interpretation | Error code | Port closed | Review |
|---:|---|---|---|---|---:|---|---|---|---|
| 1 | Stationary / `SERVO_STATUS` | | | | | | | | |
| 2 | Optional / `PLAN_OPERATION_GROUP` | | | | | | | | |
| 3 | Neither switch / `DI_STATUS` | | | | | | | | |
| 4 | PL manually actuated / `DI_STATUS` | | | | | | | | |
| 5 | PL released / `DI_STATUS` | | | | | | | | |
| 6 | NL manually actuated / `DI_STATUS` | | | | | | | | |
| 7 | NL released / `DI_STATUS` | | | | | | | | |

### DI observations

| Item | Baseline raw bit | Actuated raw bit | Released raw bit | Installed assignment verified? | Active level conclusion |
|---|---|---|---|---|---|
| PL | | | | | `ACTIVE_LEVEL_UNVERIFIED` / high / low |
| NL | | | | | `ACTIVE_LEVEL_UNVERIFIED` / high / low |

Physical simultaneous PL+NL activation performed? **No** / separately assessed and approved:
____________________. Simulation contradiction result: ____________________.

## Stop Point C - review and closure

| Evidence class | Findings |
|---|---|
| Confirmed by documentation | |
| Supported by historical operation | |
| Verified on current hardware | |
| Unresolved | |
| Not required for first read-only test | |

- [ ] No motion occurred.
- [ ] No Servo On or Fault Reset occurred.
- [ ] No register write or setting change occurred.
- [ ] No retry, scan, polling, discovery, or automatic reconnect occurred.
- [ ] Every opened port was closed and raw captures were retained.
- [ ] Results were reviewed before any proposal for a later milestone.

Final decision: ____________________. Reviewer/date: ____________________.

**Completion of Session 1 does not authorize motion.**
